"""Property tests for CID core functionality."""

from hypothesis import assume, example, given, strategies as st

from cid_core import (
    CID_LENGTH_PREFIX_CHARS,
    CID_MIN_LENGTH,
    CID_MIN_REFERENCE_LENGTH,
    CID_NORMALIZED_PATTERN,
    CID_REFERENCE_PATTERN,
    CID_STRICT_PATTERN,
    MAX_CONTENT_LENGTH,
    base64url_decode,
    base64url_encode,
    normalize_component,
)


# ============================================================================
# Strategies
# ============================================================================


def base64url_safe_bytes():
    """Generate bytes suitable for base64url encoding."""
    return st.binary(min_size=0, max_size=200)


def whitespace():
    """Generate various whitespace patterns."""
    return st.text(alphabet=" \t\n\r", min_size=0, max_size=5)


def cid_like_strings():
    """Generate strings that look like CID components."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="_-",
        ),
        min_size=CID_MIN_REFERENCE_LENGTH,
        max_size=100,
    )


# ============================================================================
# Property Tests
# ============================================================================


@given(base64url_safe_bytes())
@example(b"")
@example(b"hello world")
@example(b"\x00\xff\x00\xff")
def test_base64url_encode_decode_round_trip(data):
    """Encoding bytes and decoding back should yield original data."""
    encoded = base64url_encode(data)
    decoded = base64url_decode(encoded)
    
    assert decoded == data


@given(base64url_safe_bytes())
@example(b"test")
@example(b"x" * 100)
def test_base64url_encode_no_padding(data):
    """Base64url encoding should not include padding characters."""
    encoded = base64url_encode(data)
    
    assert "=" not in encoded
    assert isinstance(encoded, str)


@given(cid_like_strings())
@example("abc123")
@example("TEST_VALUE-123")
def test_normalize_component_idempotence(value):
    """Normalizing a component multiple times should yield the same result."""
    normalized_once = normalize_component(value)
    normalized_twice = normalize_component(normalized_once)
    
    assert normalized_once == normalized_twice


@given(cid_like_strings(), whitespace(), whitespace())
@example("abc123", " ", " ")
@example("test", "  ", "\t")
def test_normalize_component_strips_whitespace(value, prefix_ws, suffix_ws):
    """Normalization should strip leading and trailing whitespace."""
    with_whitespace = f"{prefix_ws}{value}{suffix_ws}"
    normalized = normalize_component(with_whitespace)
    
    # Should have no leading/trailing whitespace
    assert normalized == normalized.strip()


@given(cid_like_strings())
@example("abc123")
@example("test")
def test_normalize_component_strips_leading_slashes(value):
    """Normalization should strip leading slashes."""
    with_slash = f"/{value}"
    with_multiple_slashes = f"///{value}"
    
    assert normalize_component(with_slash) == normalize_component(value)
    assert normalize_component(with_multiple_slashes) == normalize_component(value)


@given(cid_like_strings(), cid_like_strings())
@example("abc", "def")
@example("test1", "test2")
def test_normalize_component_rejects_internal_slashes(part1, part2):
    """Normalization should return empty string for paths with internal slashes."""
    with_internal_slash = f"{part1}/{part2}"
    normalized = normalize_component(with_internal_slash)
    
    assert normalized == ""


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="_-",
        ),
        min_size=CID_MIN_LENGTH,
        max_size=100,
    )
)
@example("A" * CID_MIN_LENGTH)
@example("abc123DEF_-")
def test_cid_validation_pattern_consistency(cid_string):
    """If a string matches CID_STRICT_PATTERN, it should also match broader patterns."""
    strict_match = bool(CID_STRICT_PATTERN.fullmatch(cid_string))
    reference_match = bool(CID_REFERENCE_PATTERN.fullmatch(cid_string))
    normalized_match = bool(CID_NORMALIZED_PATTERN.fullmatch(cid_string))
    
    if strict_match:
        # Strict pattern is most restrictive, should match reference pattern
        assert reference_match, "Strict CID should match reference pattern"
    
    if normalized_match:
        # Normalized CID should match reference pattern
        assert reference_match, "Normalized CID should match reference pattern"


@given(st.integers(min_value=0, max_value=MAX_CONTENT_LENGTH))
@example(0)
@example(64)
@example(MAX_CONTENT_LENGTH)
def test_cid_length_encoding_size(length):
    """Encoded CID length should always be exactly CID_LENGTH_PREFIX_CHARS."""
    from cid_utils import encode_cid_length
    
    encoded = encode_cid_length(length)
    
    assert len(encoded) == CID_LENGTH_PREFIX_CHARS
    assert isinstance(encoded, str)


@given(st.integers(min_value=0, max_value=MAX_CONTENT_LENGTH))
@example(0)
@example(1024)
@example(MAX_CONTENT_LENGTH)
def test_cid_length_encode_decode_round_trip(length):
    """Encoding and decoding CID length should round-trip correctly."""
    from cid_utils import encode_cid_length, parse_cid_components, _base64url_encode
    
    # Create a minimal CID with just the length prefix
    # For lengths <= 64, we embed content; for > 64, we use digest
    if length <= 64:
        # Use empty content of the right length
        content = b"\x00" * length
        cid = f"{encode_cid_length(length)}{_base64url_encode(content)}"
    else:
        # Use a dummy digest (SHA-512 size)
        digest = b"\x00" * 64
        cid = f"{encode_cid_length(length)}{_base64url_encode(digest)}"
    
    decoded_length, _ = parse_cid_components(cid)
    
    assert decoded_length == length


@given(base64url_safe_bytes())
@example(b"test data")
@example(b"")
def test_base64url_decode_handles_no_padding(data):
    """Base64url decode should handle strings without padding."""
    encoded_with_padding = base64url_encode(data)
    # Remove any padding that might exist
    encoded_no_padding = encoded_with_padding.rstrip("=")
    
    decoded = base64url_decode(encoded_no_padding)
    assert decoded == data


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="_-",
        ),
        min_size=0,
        max_size=CID_MIN_REFERENCE_LENGTH - 1,
    )
)
@example("")
@example("abc")
def test_short_strings_not_cid_references(short_string):
    """Strings shorter than minimum reference length should not match CID patterns."""
    assume(len(short_string) < CID_MIN_REFERENCE_LENGTH)
    
    reference_match = bool(CID_REFERENCE_PATTERN.fullmatch(short_string))
    
    assert not reference_match


@given(st.none() | st.just(""))
@example(None)
@example("")
def test_normalize_component_handles_none_and_empty(value):
    """Normalization should handle None and empty strings gracefully."""
    result = normalize_component(value)
    
    assert result == ""
    assert isinstance(result, str)


@given(
    st.text(min_size=1, max_size=50).filter(lambda s: "/" not in s and s.strip() != "")
)
@example("validCID123")
@example("another_test-value")
def test_normalize_preserves_valid_components(value):
    """Normalization should preserve valid CID components without slashes."""
    assume("/" not in value)
    assume(value.strip() != "")
    
    normalized = normalize_component(value)
    
    # Should preserve the component (minus any leading/trailing whitespace)
    assert normalized == value.strip().lstrip("/")
