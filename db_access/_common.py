"""Common utilities and constants shared across db_access modules."""

from datetime import datetime, timezone
from typing import TypeVar

from database import db

# Type variable for entity operations
T = TypeVar('T')

# Constants
DEFAULT_AI_SERVER_NAME = "ai_stub"
DEFAULT_AI_ALIAS_NAME = "ai"
DEFAULT_CSS_ALIAS_NAME = "CSS"
DEFAULT_ACTION = "save"
MAX_MESSAGE_LENGTH = 500


def save_entity(entity: T) -> T:
    """Save an entity to the database and commit the transaction."""
    db.session.add(entity)
    db.session.commit()
    return entity


def delete_entity(entity: T) -> None:
    """Delete an entity from the database and commit the transaction."""
    db.session.delete(entity)
    db.session.commit()


def rollback_session() -> None:
    """Roll back the current database session."""
    db.session.rollback()


def ensure_utc_timestamp(dt: datetime | None) -> datetime | None:
    """Convert timestamp to UTC, handling naive and aware datetimes."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_cid_value(value: str | None) -> str:
    """Return a normalized CID component without leading slashes or whitespace."""
    if value is None:
        return ""
    normalized = value.strip().lstrip("/")
    return normalized

