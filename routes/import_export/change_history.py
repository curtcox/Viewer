"""Change history serialization, gathering, and import operations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Iterable, Tuple

from db_access import (
    EntityInteractionLookup,
    EntityInteractionRequest,
    find_entity_interaction,
    get_entity_interactions,
    get_user_aliases,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    record_entity_interaction,
)


def serialise_interaction_history(user_id: str, entity_type: str, entity_name: str) -> list[dict[str, str]]:
    """Serialize interaction history for a single entity."""
    interactions = get_entity_interactions(user_id, entity_type, entity_name)

    history: list[dict[str, str]] = []
    for interaction in interactions:
        timestamp = interaction.created_at
        if timestamp is None:
            continue
        aware = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        aware = aware.astimezone(timezone.utc)
        history.append(
            {
                'timestamp': aware.isoformat(),
                'message': (interaction.message or '').strip(),
                'action': (interaction.action or '').strip() or 'save',
            }
        )

    return history


def gather_change_history(user_id: str) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Return change history grouped by entity collection."""
    collections: dict[str, tuple[str, Iterable[str]]] = {
        'aliases': ('alias', (alias.name for alias in get_user_aliases(user_id))),
        'servers': ('server', (server.name for server in get_user_servers(user_id))),
        'variables': ('variable', (variable.name for variable in get_user_variables(user_id))),
        'secrets': ('secret', (secret.name for secret in get_user_secrets(user_id))),
    }

    history_payload: dict[str, dict[str, list[dict[str, str]]]] = {}

    for key, (entity_type, names) in collections.items():
        collection_history: dict[str, list[dict[str, str]]] = {}
        for name in names:
            events = serialise_interaction_history(user_id, entity_type, name)
            if events:
                collection_history[name] = events
        if collection_history:
            history_payload[key] = collection_history

    return history_payload


def parse_history_timestamp(value: str) -> datetime | None:
    """Parse an ISO timestamp string into a datetime object."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith('Z'):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass
class HistoryEvent:
    """Normalized history event from import payload."""

    timestamp: datetime
    action: str
    message: str
    content: str


def normalise_history_name(
    collection_key: str,
    raw_name: Any,
    errors: list[str],
) -> str | None:
    """Normalize and validate a history entry name."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        errors.append(f'{collection_key.title()} history entry must include a valid item name.')
        return None
    return raw_name.strip()


def prepare_history_event(
    name: str,
    raw_event: Any,
    errors: list[str],
) -> HistoryEvent | None:
    """Parse and validate a history event from import payload."""
    if not isinstance(raw_event, dict):
        errors.append(f'History events for "{name}" must be objects.')
        return None

    timestamp_raw = raw_event.get('timestamp')
    timestamp = parse_history_timestamp(timestamp_raw or '')
    if timestamp is None:
        errors.append(f'History event for "{name}" has an invalid timestamp.')
        return None

    action_raw = raw_event.get('action')
    action = (action_raw if isinstance(action_raw, str) else '').strip() or 'save'
    message_raw = raw_event.get('message')
    message = (message_raw if isinstance(message_raw, str) else '').strip()
    if len(message) > 500:
        message = message[:497] + '…'
    content_raw = raw_event.get('content')
    content = (content_raw if isinstance(content_raw, str) else '').strip()

    return HistoryEvent(
        timestamp=timestamp,
        action=action,
        message=message,
        content=content,
    )


def iter_history_events(
    raw_history: dict[str, Any],
    collection_key: str,
    errors: list[str],
) -> Iterator[tuple[str, HistoryEvent]]:
    """Iterate over history events for a collection."""
    entries = raw_history.get(collection_key)
    if entries is None:
        return
    if not isinstance(entries, dict):
        errors.append(f'{collection_key.title()} history must map item names to event lists.')
        return

    for raw_name, raw_events in entries.items():
        name = normalise_history_name(collection_key, raw_name, errors)
        if not name:
            continue
        if not isinstance(raw_events, list):
            errors.append(f'History for "{raw_name}" must be a list of events.')
            continue
        for raw_event in raw_events:
            event = prepare_history_event(name, raw_event, errors)
            if event is not None:
                yield name, event


def import_change_history(user_id: str, raw_history: Any) -> Tuple[int, list[str]]:
    """Import change history events."""
    if raw_history is None:
        return 0, ['No change history data found in import file.']
    if not isinstance(raw_history, dict):
        return 0, ['Change history in import file must be an object mapping collections to events.']

    collection_map = {
        'aliases': 'alias',
        'servers': 'server',
        'variables': 'variable',
        'secrets': 'secret',
    }

    errors: list[str] = []
    imported = 0

    for key, entity_type in collection_map.items():
        for name, event in iter_history_events(raw_history, key, errors):
            existing = find_entity_interaction(
                EntityInteractionLookup(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_name=name,
                    action=event.action,
                    message=event.message,
                    created_at=event.timestamp,
                )
            )
            if existing:
                continue

            record_entity_interaction(
                EntityInteractionRequest(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_name=name,
                    action=event.action,
                    message=event.message,
                    content=event.content,
                    created_at=event.timestamp,
                )
            )
            imported += 1

    return imported, errors
