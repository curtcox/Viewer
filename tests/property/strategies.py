"""Hypothesis strategies for in-memory vs disk database equivalence tests."""

from __future__ import annotations

from hypothesis import strategies as st


SERVER_NAME_CHARS = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    whitelist_characters="-_",
)

server_names = (
    st.text(SERVER_NAME_CHARS, min_size=1, max_size=40)
    .map(lambda value: value.strip("-_") or "srv")
    .map(lambda value: value[:40])
)

definitions = st.text(min_size=1, max_size=1000)

binary_cid_data = st.binary(min_size=0, max_size=1024)

server_records = st.fixed_dictionaries(
    {
        "name": server_names,
        "definition": definitions,
        "enabled": st.booleans(),
    }
)
