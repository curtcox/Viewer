"""Shared helpers for parsing and formatting history timestamps."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class ParsedDateRange:
    """Normalized inputs and parsed datetimes for a date range filter."""

    start_at: Optional[datetime]
    end_at: Optional[datetime]
    start_value: str
    end_value: str
    start_valid: bool
    end_valid: bool

    @property
    def filters(self) -> dict[str, str]:
        """Return query parameters for linking to this date range."""
        params: dict[str, str] = {}
        if self.start_at:
            params["start"] = self.start_value
        if self.end_at:
            params["end"] = self.end_value
        return params


def parse_date_range(start_raw: Optional[str], end_raw: Optional[str]) -> ParsedDateRange:
    """Parse start/end inputs while preserving user intent and validity."""

    start_raw = start_raw or ""
    end_raw = end_raw or ""

    start_trimmed = start_raw.strip()
    end_trimmed = end_raw.strip()

    start_at = parse_history_timestamp(start_trimmed) if start_trimmed else None
    end_at = parse_history_timestamp(end_trimmed) if end_trimmed else None

    start_valid = not start_trimmed or start_at is not None
    end_valid = not end_trimmed or end_at is not None

    start_value = format_history_timestamp(start_at) if start_at else start_trimmed
    end_value = format_history_timestamp(end_at) if end_at else end_trimmed

    return ParsedDateRange(
        start_at=start_at,
        end_at=end_at,
        start_value=start_value,
        end_value=end_value,
        start_valid=start_valid,
        end_valid=end_valid,
    )


__all__ = [
    "HISTORY_TIMESTAMP_FORMAT",
    "format_history_timestamp",
    "parse_history_timestamp",
    "parse_date_range",
    "ParsedDateRange",
]
