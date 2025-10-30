"""Property-based tests for response format transformations."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from hypothesis import given, strategies as st

from response_formats import _value_to_xml


def _composite_strategy() -> st.SearchStrategy[object]:
    scalars = st.one_of(st.integers(), st.text(), st.booleans(), st.none())
    return st.recursive(
        scalars,
        lambda children: st.one_of(
            st.lists(children, max_size=4),
            st.dictionaries(st.text(min_size=1, max_size=8), children, max_size=4),
        ),
        max_leaves=10,
    )


@given(_composite_strategy())
def test_value_to_xml_produces_parseable_documents(payload) -> None:
    xml_document = _value_to_xml(payload, "response")
    ET.fromstring(xml_document)
