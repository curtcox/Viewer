"""Property tests for history filters."""

from datetime import datetime, timezone, timedelta
from hypothesis import assume, example, given, strategies as st
import pytest

from history_filters import (
    HISTORY_TIMESTAMP_FORMAT,
    format_history_timestamp,
    parse_history_timestamp,
    parse_date_range,
    ParsedDateRange,
)


# ============================================================================
# Strategies
# ============================================================================


def timezone_aware_datetimes():
    """Generate timezone-aware datetimes."""
    return st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2099, 12, 31),
    ).map(lambda dt: dt.replace(tzinfo=timezone.utc))


def timezone_offsets():
    """Generate timezone offsets."""
    return st.integers(min_value=-12, max_value=14).map(
        lambda hours: timezone(timedelta(hours=hours))
    )


# ============================================================================
# Property Tests
# ============================================================================


@given(timezone_aware_datetimes())
@example(datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc))
@example(datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
def test_timestamp_round_trip(dt):
    """Formatting a datetime and parsing it back should yield the original value."""
    formatted = format_history_timestamp(dt)
    parsed = parse_history_timestamp(formatted)
    
    # Should round-trip correctly (comparing in UTC)
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    
    # Should be equal when both are in UTC (within seconds precision)
    dt_utc = dt.astimezone(timezone.utc)
    # Format only includes seconds precision, so microseconds will be lost
    assert parsed.replace(microsecond=0) == dt_utc.replace(microsecond=0)


@given(timezone_aware_datetimes(), timezone_offsets())
@example(datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc), timezone(timedelta(hours=5)))
@example(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), timezone(timedelta(hours=-8)))
def test_timezone_normalization(dt, tz_offset):
    """All timestamps should be normalized to UTC."""
    # Convert to a different timezone
    dt_in_offset = dt.astimezone(tz_offset)
    
    formatted = format_history_timestamp(dt_in_offset)
    parsed = parse_history_timestamp(formatted)
    
    # Parsed result should always be in UTC
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    
    # The actual time should match the original UTC time
    dt_utc = dt.astimezone(timezone.utc)
    assert parsed.replace(microsecond=0) == dt_utc.replace(microsecond=0)


@given(st.none() | st.just(""))
@example(None)
@example("")
@example("   ")
def test_parse_empty_timestamp(value):
    """Empty or None timestamps should return None."""
    result = parse_history_timestamp(value)
    assert result is None


@given(st.text(min_size=1, max_size=50).filter(lambda s: s.strip() and "/" not in s))
@example("invalid")
@example("not a date")
@example("2024-13-45 99:99:99")
def test_parse_invalid_timestamp_returns_none(invalid_str):
    """Invalid timestamp strings should return None."""
    result = parse_history_timestamp(invalid_str)
    assert result is None


@given(st.none())
@example(None)
def test_format_none_timestamp(value):
    """Formatting None should return empty string."""
    result = format_history_timestamp(value)
    assert result == ""


@given(
    st.one_of(st.none(), st.just("")),
    st.one_of(st.none(), st.just("")),
)
@example(None, None)
@example("", "")
def test_parse_date_range_never_raises(start_raw, end_raw):
    """parse_date_range should handle any pair of inputs gracefully."""
    # Should never raise an exception
    result = parse_date_range(start_raw, end_raw)
    
    assert isinstance(result, ParsedDateRange)
    assert isinstance(result.start_valid, bool)
    assert isinstance(result.end_valid, bool)


@given(timezone_aware_datetimes(), timezone_aware_datetimes())
@example(
    datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
)
def test_parse_date_range_valid_dates(start_dt, end_dt):
    """Valid date range should parse correctly."""
    start_str = format_history_timestamp(start_dt)
    end_str = format_history_timestamp(end_dt)
    
    result = parse_date_range(start_str, end_str)
    
    assert result.start_valid is True
    assert result.end_valid is True
    assert result.start_at is not None
    assert result.end_at is not None
    
    # Values should round-trip through format
    assert result.start_value == start_str
    assert result.end_value == end_str


@given(st.text(min_size=1, max_size=50).filter(lambda s: "/" not in s and s.strip() != ""))
@example("invalid_date")
@example("bad format")
def test_parse_date_range_invalid_dates(invalid_str):
    """Invalid date strings should be marked as invalid."""
    # Make sure the string isn't accidentally a valid date when stripped
    assume(parse_history_timestamp(invalid_str.strip()) is None)
    
    result = parse_date_range(invalid_str, invalid_str)
    
    # Both should be marked invalid
    assert result.start_valid is False
    assert result.end_valid is False
    
    # Original values should be preserved (after stripping)
    assert result.start_value == invalid_str.strip()
    assert result.end_value == invalid_str.strip()


@given(timezone_aware_datetimes())
@example(datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc))
def test_date_range_filters_property(dt):
    """The filters property should contain values that can be parsed back."""
    dt_str = format_history_timestamp(dt)
    
    result = parse_date_range(dt_str, dt_str)
    filters = result.filters
    
    # Should have both start and end
    assert "start" in filters
    assert "end" in filters
    
    # Values should be parseable back to datetimes
    reparsed_start = parse_history_timestamp(filters["start"])
    reparsed_end = parse_history_timestamp(filters["end"])
    
    assert reparsed_start is not None
    assert reparsed_end is not None


@given(timezone_aware_datetimes())
@example(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
def test_formatted_timestamp_has_no_timezone_suffix(dt):
    """Formatted timestamps should not include timezone suffix (always UTC)."""
    formatted = format_history_timestamp(dt)
    
    # Should not contain timezone indicators
    assert "UTC" not in formatted
    assert "+00:00" not in formatted
    assert "Z" not in formatted
    
    # Should match the expected format
    try:
        datetime.strptime(formatted, HISTORY_TIMESTAMP_FORMAT)
    except ValueError:
        pytest.fail(f"Formatted timestamp '{formatted}' doesn't match format")


@given(st.none(), st.none())
@example(None, None)
def test_date_range_empty_inputs_valid(start_raw, end_raw):
    """Empty date range inputs should be considered valid."""
    result = parse_date_range(start_raw, end_raw)
    
    # Empty inputs are valid (just no filtering)
    assert result.start_valid is True
    assert result.end_valid is True
    assert result.start_at is None
    assert result.end_at is None


@given(timezone_aware_datetimes())
@example(datetime(2024, 7, 4, 15, 30, 0, tzinfo=timezone.utc))
def test_timestamp_format_idempotent(dt):
    """Formatting twice should yield the same result."""
    formatted_once = format_history_timestamp(dt)
    
    # Parse and format again
    parsed = parse_history_timestamp(formatted_once)
    formatted_twice = format_history_timestamp(parsed)
    
    assert formatted_once == formatted_twice
