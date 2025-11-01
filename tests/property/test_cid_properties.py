"""Property tests for CID encoding and parsing."""

from hypothesis import example, given, strategies as st

from cid_utils import (
    DIRECT_CONTENT_EMBED_LIMIT,
    MAX_CONTENT_LENGTH,
    SHA512_DIGEST_SIZE,
    _base64url_encode,
    encode_cid_length,
    parse_cid_components,
)


def hashed_cid_inputs():
    """Return a strategy that yields hashed CID length/digest pairs."""

    length_strategy = st.integers(
        min_value=DIRECT_CONTENT_EMBED_LIMIT + 1, max_value=MAX_CONTENT_LENGTH
    )
    digest_strategy = st.binary(
        min_size=SHA512_DIGEST_SIZE, max_size=SHA512_DIGEST_SIZE
    )
    return st.tuples(length_strategy, digest_strategy)


def embedded_cid_inputs():
    """Return a strategy that yields embedded CID length/content pairs."""

    length_strategy = st.integers(min_value=0, max_value=DIRECT_CONTENT_EMBED_LIMIT)

    def content_for_length(length: int) -> st.SearchStrategy[bytes]:
        return st.binary(min_size=length, max_size=length)

    return length_strategy.flatmap(
        lambda length: st.tuples(st.just(length), content_for_length(length))
    )


@given(hashed_cid_inputs())
@example((DIRECT_CONTENT_EMBED_LIMIT + 1, b"\x00" * SHA512_DIGEST_SIZE))
@example((MAX_CONTENT_LENGTH, b"\xff" * SHA512_DIGEST_SIZE))
def test_hashed_encode_parse_round_trip(cid_components):
    """Round-tripping hashed CID components preserves the digest."""

    length, digest = cid_components
    cid = f"{encode_cid_length(length)}{_base64url_encode(digest)}"
    parsed_length, parsed_digest = parse_cid_components(cid)

    assert parsed_length == length
    assert parsed_digest == digest


@given(embedded_cid_inputs())
@example((0, b""))
@example((DIRECT_CONTENT_EMBED_LIMIT, b"\x00" * DIRECT_CONTENT_EMBED_LIMIT))
def test_embedded_encode_parse_round_trip(cid_components):
    """Round-tripping embedded CID components preserves the content."""

    length, content = cid_components
    cid = f"{encode_cid_length(length)}{_base64url_encode(content)}"
    parsed_length, parsed_content = parse_cid_components(cid)

    assert parsed_length == length
    assert parsed_content == content
