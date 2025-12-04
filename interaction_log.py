"""Helpers for presenting entity interaction history."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Dict, Iterable, List

from db_access import get_recent_entity_interactions
from models import EntityInteraction

_PREVIEW_LENGTH = 80


def _truncate_preview(text: str) -> str:
    """Limit preview text to a friendly length."""

    if len(text) <= _PREVIEW_LENGTH:
        return text
    return text[: _PREVIEW_LENGTH - 1] + '…'


def summarise_interaction(interaction: EntityInteraction) -> Dict[str, Any]:
    """Convert an interaction into a template-friendly dictionary."""

    message = (interaction.message or '').strip()
    preview_source = message or '(no message provided)'
    preview = _truncate_preview(preview_source)
    created_at = interaction.created_at
    if created_at is None:
        timestamp_display = ''
        timestamp_iso = ''
        timestamp_url = ''
        timestamp_url_end = ''
    else:
        aware = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        timestamp_iso = aware.astimezone(timezone.utc).isoformat()
        timestamp_display = aware.strftime('%Y-%m-%d %H:%M UTC')
        # Format for URL parameters in /history and /server_events
        from datetime import timedelta
        from history_filters import format_history_timestamp
        timestamp_url = format_history_timestamp(aware)
        # End timestamp is one second after start to include the entire second in the range
        timestamp_url_end = format_history_timestamp(aware + timedelta(seconds=1))

    action = (interaction.action or '').lower() or 'save'
    if action == 'ai':
        action_display = 'AI'
    elif action == 'save':
        action_display = 'Saved'
    else:
        action_display = action.title()

    return {
        'id': interaction.id,
        'action': action,
        'action_display': action_display,
        'timestamp': timestamp_display,
        'timestamp_iso': timestamp_iso,
        'timestamp_url': timestamp_url,
        'timestamp_url_end': timestamp_url_end,
        'message': message,
        'preview': preview,
        'content': interaction.content or '',
    }


def summarise_interactions(interactions: Iterable[EntityInteraction]) -> List[Dict[str, Any]]:
    """Summarise a collection of interactions."""

    return [summarise_interaction(item) for item in interactions]


def load_interaction_history(
    entity_type: str,
    entity_name: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Load and summarise the most recent interactions for an entity."""

    interactions = get_recent_entity_interactions(entity_type, entity_name, limit)
    return summarise_interactions(interactions)


__all__ = ['summarise_interaction', 'summarise_interactions', 'load_interaction_history']
