"""Property tests for entity reference helpers."""

from hypothesis import given, strategies as st

from entity_references import _dedupe, _normalize_local_path, _strip_extension


@given(st.sampled_from(["http", "https", "ftp", "file", "mailto"]))
def test_normalize_local_path_rejects_urls_with_schemes(scheme):
    value = f"{scheme}://example.com/path"
    assert _normalize_local_path(value) is None


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_/.",
        ),
        min_size=1,
        max_size=200,
    )
)
def test_normalize_local_path_adds_leading_slash(path):
    normalized = _normalize_local_path(f"  {path.lstrip('/')}  ")
    assert normalized is not None
    assert normalized.startswith("/")
    assert normalized.lstrip("/") == path.lstrip("/")


@given(st.lists(st.one_of(st.none(), st.text(min_size=0, max_size=20)), min_size=0, max_size=50))
def test_dedupe_removes_duplicates_and_preserves_first_seen_order(values):
    entries = [{"name": value} for value in values if value is not None]
    deduped = _dedupe(entries, "name")

    seen = set()
    expected = []
    for entry in entries:
        identifier = entry.get("name")
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        expected.append(entry)

    assert deduped == expected


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_/.",
        ),
        min_size=1,
        max_size=200,
    )
)
def test_strip_extension_only_strips_from_last_segment(path):
    if "/" in path:
        prefix, last = path.rsplit("/", 1)
        prefix = f"{prefix}/" if prefix else "/"
    else:
        prefix, last = "", path

    stripped = _strip_extension(path)

    if "." not in last:
        assert stripped == path
        return

    base = last.split(".", 1)[0]
    assert stripped.endswith(base)
    assert stripped.startswith(prefix.rstrip("/"))
