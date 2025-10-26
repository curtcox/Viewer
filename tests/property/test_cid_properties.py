"""Property tests for CID encoding and parsing."""

from hypothesis import example, given, strategies as st

from cid_utils import (
    MAX_CONTENT_LENGTH,
    SHA512_DIGEST_SIZE,
    _base64url_encode,
    encode_cid_length,
    parse_cid_components,
)


def cid_inputs():
    """Return a strategy that yields CID length/digest pairs."""

    length_strategy = st.integers(min_value=0, max_value=MAX_CONTENT_LENGTH)
    digest_strategy = st.binary(
        min_size=SHA512_DIGEST_SIZE, max_size=SHA512_DIGEST_SIZE
    )
    return st.tuples(length_strategy, digest_strategy)


@given(cid_inputs())
@example((0, b"\x00" * SHA512_DIGEST_SIZE))
@example((MAX_CONTENT_LENGTH, b"\xff" * SHA512_DIGEST_SIZE))
def test_encode_parse_round_trip(cid_components):
    """Round-tripping the CID components preserves the values."""

    length, digest = cid_components
    cid = f"{encode_cid_length(length)}{_base64url_encode(digest)}"
    parsed_length, parsed_digest = parse_cid_components(cid)

    assert parsed_length == length
    assert parsed_digest == digest
