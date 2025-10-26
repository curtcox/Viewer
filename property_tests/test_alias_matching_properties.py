"""Property-based tests for alias matching helpers."""
from __future__ import annotations

from hypothesis import assume, given, strategies as st

from alias_matching import matches_path, normalise_pattern

_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n"),
    max_size=32,
)


@given(pattern=_text, fallback=_text)
def test_normalise_literal_paths_generate_clean_slashes(pattern: str, fallback: str) -> None:
    """Literal patterns should always normalise to a clean, slash-prefixed path."""
    assume(pattern.strip() or fallback.strip())

    normalised = normalise_pattern("literal", pattern, fallback)

    assert normalised.startswith("/")
    if normalised != "/":
        assert not normalised.endswith("/")

    assert matches_path("literal", normalised, normalised)
    assert matches_path("literal", normalised, normalised + "/")
    assert matches_path("literal", normalised.lower(), normalised.upper(), ignore_case=True)
