"""Property tests for link presenter helpers."""

from hypothesis import given, strategies as st

from link_presenter import _combine_base_url, _normalize_segment, alias_path, server_path


@given(st.one_of(st.none(), st.text(min_size=0, max_size=200)))
def test_normalize_segment_is_idempotent(value):
    first = _normalize_segment(value)
    second = _normalize_segment(first)
    assert first == second


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_",
        ),
        min_size=1,
        max_size=100,
    )
)
def test_server_path_treats_servers_prefix_as_optional(name):
    cleaned = name.strip("/")
    assert server_path(cleaned) == server_path(f"servers/{cleaned}")


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_",
        ),
        min_size=1,
        max_size=40,
    )
)
def test_combine_base_url_strips_trailing_slash(base_segment):
    base = f"https://example.com/{base_segment}/"
    path = alias_path("docs")
    combined = _combine_base_url(base, path)
    assert combined == f"https://example.com/{base_segment}{path}"
