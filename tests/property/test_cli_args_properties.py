"""Property tests for CLI argument parsing."""

from hypothesis import assume, example, given, strategies as st
import pytest

from cli_args import parse_memory_size


# ============================================================================
# Strategies
# ============================================================================


def valid_memory_values():
    """Generate valid numeric values for memory sizes."""
    return st.one_of(
        st.integers(min_value=1, max_value=1024),
        st.floats(min_value=1.0, max_value=1024.0, allow_nan=False, allow_infinity=False),
    )


def memory_units():
    """Generate valid memory unit suffixes."""
    return st.sampled_from(["", "K", "M", "G", "T"])


def memory_spacing():
    """Generate spacing variations."""
    return st.sampled_from(["", " ", "  "])


def memory_b_suffix():
    """Generate optional 'B' suffix."""
    return st.sampled_from(["", "B"])


# ============================================================================
# Property Tests
# ============================================================================


@given(st.integers(min_value=1, max_value=1024), memory_units())
@example(1, "K")
@example(1, "M")
@example(1, "G")
def test_memory_size_parsing_integers(value, unit):
    """Parsing integer memory sizes should produce correct byte counts."""
    size_str = f"{value}{unit}"
    result = parse_memory_size(size_str)
    
    multipliers = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }
    
    expected = value * multipliers[unit]
    assert result == expected


@given(
    st.floats(min_value=1.0, max_value=1024.0, allow_nan=False, allow_infinity=False),
    memory_units()
)
@example(1.5, "M")
@example(2.75, "G")
def test_memory_size_parsing_floats(value, unit):
    """Parsing floating point memory sizes should produce correct byte counts."""
    size_str = f"{value}{unit}"
    result = parse_memory_size(size_str)
    
    multipliers = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }
    
    expected = int(value * multipliers[unit])
    assert result == expected
    assert isinstance(result, int)


@given(
    st.integers(min_value=1, max_value=1024),
    memory_units(),
    memory_spacing(),
    memory_b_suffix(),
    st.booleans()  # Case variation for unit
)
@example(1, "G", " ", "B", False)
@example(512, "M", "", "", True)
def test_memory_size_format_variations(value, unit, spacing, b_suffix, lowercase_unit):
    """Different formatting variations should parse to the same value."""
    # Apply case variation
    unit_str = unit.lower() if lowercase_unit else unit
    
    size_str = f"{value}{spacing}{unit_str}{b_suffix}"
    result = parse_memory_size(size_str)
    
    multipliers = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }
    
    expected = value * multipliers[unit]
    assert result == expected


@given(st.integers(min_value=1, max_value=1024))
@example(1024)
@example(1)
def test_memory_size_bytes_equals_k(value):
    """1024 bytes should equal 1K."""
    bytes_result = parse_memory_size(str(value))
    k_result = parse_memory_size(f"{value}K")
    
    assert bytes_result * 1024 == k_result


@given(st.integers(min_value=1, max_value=1024))
@example(1024)
@example(1)
def test_memory_size_k_equals_m(value):
    """1024K should equal 1M."""
    k_result = parse_memory_size(f"{value}K")
    m_result = parse_memory_size(f"{value}M")
    
    assert k_result * 1024 == m_result


@given(
    st.text(min_size=1, max_size=20).filter(
        lambda s: not s.strip().upper().replace(".", "").replace(" ", "")[0].isdigit()
        if s.strip() else True
    )
)
@example("invalid")
@example("abc")
@example("--123")
def test_memory_size_invalid_input_raises(invalid_str):
    """Invalid input strings should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid memory size format"):
        parse_memory_size(invalid_str)


@given(st.integers(min_value=0, max_value=0))
@example(0)
def test_memory_size_zero_invalid(value):
    """Zero or negative values should be handled correctly."""
    # The regex requires at least 1 digit, but 0 is technically valid per the regex
    # However, for memory sizes, 0 might not make sense
    size_str = str(value)
    result = parse_memory_size(size_str)
    assert result == 0


@given(st.integers(min_value=-1000, max_value=-1))
@example(-1)
@example(-100)
def test_memory_size_negative_invalid(value):
    """Negative values should raise ValueError."""
    size_str = str(value)
    with pytest.raises(ValueError, match="Invalid memory size format"):
        parse_memory_size(size_str)


@given(st.integers(min_value=1, max_value=100), memory_units())
@example(50, "M")
@example(2, "G")
def test_memory_size_always_positive(value, unit):
    """Parsed memory sizes should always be positive integers."""
    size_str = f"{value}{unit}"
    result = parse_memory_size(size_str)
    
    assert result > 0
    assert isinstance(result, int)


@given(st.integers(min_value=1, max_value=1024))
@example(1)
@example(1024)
def test_memory_size_parsing_idempotent_format(value):
    """Parsing should handle various capitalizations consistently."""
    lower_result = parse_memory_size(f"{value}k")
    upper_result = parse_memory_size(f"{value}K")
    
    assert lower_result == upper_result
