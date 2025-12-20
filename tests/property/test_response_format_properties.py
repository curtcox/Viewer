"""Property-based tests for response format transformations."""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET

from flask import Response
from hypothesis import given, strategies as st

from response_formats import _convert_response, _value_to_xml


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


def _csv_scalar_strategy() -> st.SearchStrategy[object]:
    return st.one_of(st.text(max_size=10), st.integers(), st.booleans(), st.none())


def _csv_record_strategy() -> st.SearchStrategy[dict[str, object]]:
    return st.dictionaries(
        st.text(min_size=1, max_size=6), _csv_scalar_strategy(), min_size=1, max_size=5
    )


@given(st.lists(_csv_record_strategy(), min_size=1, max_size=5))
def test_convert_response_json_to_csv_preserves_rows(
    records: list[dict[str, object]],
) -> None:
    response = Response(json.dumps(records), mimetype="application/json")

    converted = _convert_response(response, "csv")

    body = converted.get_data(as_text=True)
    reader = csv.DictReader(io.StringIO(body))
    parsed = list(reader)

    assert len(parsed) == len(records)

    fieldnames = reader.fieldnames
    assert fieldnames is not None and fieldnames, "CSV output must declare fieldnames"

    for record, row in zip(records, parsed):
        for field in fieldnames:
            expected = record.get(field)
            if expected is None:
                assert row[field] == ""
            else:
                assert row[field] == str(expected)
