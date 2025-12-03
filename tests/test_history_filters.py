"""Unit coverage for history timestamp helpers."""

from datetime import datetime, timezone

from history_filters import (
    HISTORY_TIMESTAMP_FORMAT,
    format_history_timestamp,
    parse_history_timestamp,
)


def test_format_history_timestamp_round_trips():
    moment = datetime(2025, 2, 28, 15, 35, 36, tzinfo=timezone.utc)
    formatted = format_history_timestamp(moment)
    assert formatted == "2025/02/28 15:35:36"

    parsed = parse_history_timestamp(formatted)
    assert parsed == moment


def test_parse_history_timestamp_rejects_invalid_values():
    assert parse_history_timestamp("") is None
    assert parse_history_timestamp("not a date") is None
    assert parse_history_timestamp(None) is None

