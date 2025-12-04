"""Unit coverage for history timestamp helpers."""

from datetime import datetime, timezone

from history_filters import (
    HISTORY_TIMESTAMP_FORMAT,
    ParsedDateRange,
    format_history_timestamp,
    parse_date_range,
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


def test_parse_date_range_reports_validity_and_filters():
    start_raw = "2025/02/28 15:35:36"
    end_raw = "bad-value"

    parsed = parse_date_range(start_raw, end_raw)

    assert isinstance(parsed, ParsedDateRange)
    assert parsed.start_valid is True
    assert parsed.end_valid is False
    assert parsed.start_value == start_raw
    assert parsed.end_value == end_raw
    assert parsed.start_at.strftime(HISTORY_TIMESTAMP_FORMAT) == start_raw
    assert parsed.end_at is None
    assert parsed.filters == {"start": start_raw}

