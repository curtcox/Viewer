"""Entity interaction tracking."""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from models import EntityInteraction
from database import db
from db_access._common import DEFAULT_ACTION, MAX_MESSAGE_LENGTH, ensure_utc_timestamp


@dataclass(frozen=True)
class EntityInteractionRequest:
    """Structured payload describing an interaction to persist."""

    entity_type: str
    entity_name: str
    action: str
    message: str | None
    content: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class EntityInteractionLookup:
    """Identify a previously stored interaction."""

    entity_type: str
    entity_name: str
    action: str
    message: str
    created_at: datetime | None = None


def record_entity_interaction(
    request: EntityInteractionRequest,
) -> EntityInteraction | None:
    """Persist a change or AI interaction for later recall."""
    # Skip recording in read-only mode
    from readonly_config import ReadOnlyConfig  # pylint: disable=import-outside-toplevel

    if ReadOnlyConfig.is_read_only_mode():
        return None

    if not request.entity_type or not request.entity_name:
        return None

    action_value = (request.action or "").strip() or DEFAULT_ACTION
    message_value = (request.message or "").strip()
    if len(message_value) > MAX_MESSAGE_LENGTH:
        message_value = message_value[: MAX_MESSAGE_LENGTH - 3] + "…"

    created_at_value = ensure_utc_timestamp(request.created_at)

    if created_at_value is not None:
        existing = (
            EntityInteraction.query.filter_by(
                entity_type=request.entity_type,
                entity_name=request.entity_name,
                action=action_value,
                message=message_value,
            )
            .filter(EntityInteraction.created_at == created_at_value)
            .first()
        )
        if existing:
            if request.content and request.content != existing.content:
                existing.content = request.content
                db.session.commit()
            return existing

    interaction = EntityInteraction(
        entity_type=request.entity_type,
        entity_name=request.entity_name,
        action=action_value,
        message=message_value,
        content=request.content or "",
        created_at=created_at_value,
    )
    db.session.add(interaction)
    db.session.commit()
    return interaction


def get_recent_entity_interactions(
    entity_type: str,
    entity_name: str,
    limit: int = 10,
) -> list[EntityInteraction]:
    """Fetch the most recent interactions for an entity."""
    if not entity_type or not entity_name:
        return []

    query = EntityInteraction.query.filter_by(
        entity_type=entity_type, entity_name=entity_name
    ).order_by(EntityInteraction.created_at.desc(), EntityInteraction.id.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def find_entity_interaction(
    lookup: EntityInteractionLookup,
) -> EntityInteraction | None:
    """Return a single interaction matching the supplied criteria."""
    query = EntityInteraction.query.filter_by(
        entity_type=lookup.entity_type,
        entity_name=lookup.entity_name,
        action=lookup.action,
        message=lookup.message,
    )

    if lookup.created_at is not None:
        query = query.filter(EntityInteraction.created_at == lookup.created_at)

    return query.first()


def get_entity_interactions(
    entity_type: str,
    entity_name: str,
) -> List[EntityInteraction]:
    """Return all stored interactions for an entity ordered from oldest to newest."""
    return (
        EntityInteraction.query.filter_by(
            entity_type=entity_type, entity_name=entity_name
        )
        .order_by(EntityInteraction.created_at.asc(), EntityInteraction.id.asc())
        .all()
    )
