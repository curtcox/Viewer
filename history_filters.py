"""Shared helpers for parsing and formatting history timestamps."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


HISTORY_TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%S"


def format_history_timestamp(value: Optional[datetime]) -> str:
    """Return a history timestamp string in a consistent, UTC format."""
    if value is None:
        return ""

    normalized = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return normalized.strftime(HISTORY_TIMESTAMP_FORMAT)


def parse_history_timestamp(raw_value: Optional[str]) -> Optional[datetime]:
    """Parse a history timestamp string into a timezone-aware datetime."""
    if not raw_value:
        return None

    trimmed = raw_value.strip()
    if not trimmed:
        return None

    try:
        parsed = datetime.strptime(trimmed, HISTORY_TIMESTAMP_FORMAT)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


__all__ = [
    "HISTORY_TIMESTAMP_FORMAT",
    "format_history_timestamp",
    "parse_history_timestamp",
]
