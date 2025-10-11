"""Regression tests for the Formdown showcase upload template."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List, Tuple
from urllib.parse import parse_qs, urlencode

REPO_ROOT = Path(__file__).resolve().parent
FORMDOWN_SHOWCASE_PATH = REPO_ROOT / "upload_templates" / "contents" / "formdown_showcase.formdown"


def _load_formdown_fields() -> List[dict[str, str]]:
    """Parse the formdown showcase document into field metadata."""
    document = FORMDOWN_SHOWCASE_PATH.read_text(encoding="utf-8")
    field_pattern = re.compile(
        r"^@(?P<name>[a-zA-Z0-9_]+)(?:\([^)]*\))?:\s*\[(?P<descriptor>[^\]]+)\]$",
        re.MULTILINE,
    )
    fields: List[dict[str, str]] = []
    for match in field_pattern.finditer(document):
        descriptor = match.group("descriptor").strip()
        field_type = descriptor.split()[0]
        fields.append(
            {
                "name": match.group("name"),
                "type": field_type,
                "descriptor": descriptor,
            }
        )
    return fields


def _sample_form_values() -> dict[str, object]:
    """Return representative values for each field in the showcase template."""
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+1 (555) 123-4567",
        "age": "37",
        "birth_date": "1815-12-10",
        "gender": "Non-binary",
        "skills": ["Python", "React"],
        "country": "United Kingdom",
        "experience": "Advanced",
        "preferences": ["Email Notifications", "Weekly Digest"],
        "bio": "Pioneer of computer programming.",
        "website": "https://adalovelace.example",
        "salary_range": "95000",
        "favorite_color": "#3b82f6",
        "resume": "ada-lovelace-resume.pdf",
        "portfolio": ["portfolio.pdf", "ui-mock.png"],
        "submit_form": "Submit Application",
        "reset_form": "Clear Form",
    }


EXCLUDED_TYPES = {"file", "submit", "reset"}


def _build_query_entries(
    fields: Iterable[dict[str, str]], values: dict[str, object]
) -> List[Tuple[str, str]]:
    """Return (name, value) pairs that would appear in a GET query string."""
    entries: List[Tuple[str, str]] = []
    for field in fields:
        field_name = field["name"]
        field_type = field["type"]
        if field_type in EXCLUDED_TYPES:
            continue
        raw_value = values.get(field_name)
        if raw_value is None:
            continue
        if isinstance(raw_value, list):
            for item in raw_value:
                entries.append((field_name, str(item)))
        else:
            entries.append((field_name, str(raw_value)))
    return entries


def test_formdown_showcase_includes_all_textual_field_values_in_query_string():
    fields = _load_formdown_fields()
    values = _sample_form_values()
    entries = _build_query_entries(fields, values)
    query_string = urlencode(entries)
    parsed = parse_qs(query_string, keep_blank_values=True)

    included_fields = [field for field in fields if field["type"] not in EXCLUDED_TYPES]
    assert included_fields, "Expected to discover at least one included field"

    for field in included_fields:
        expected_value = values[field["name"]]
        actual_values = parsed.get(field["name"])
        assert actual_values is not None, f"Missing {field['name']} from query string"
        if isinstance(expected_value, list):
            assert actual_values == [str(item) for item in expected_value]
        else:
            assert actual_values == [str(expected_value)]


def test_formdown_showcase_excludes_file_and_action_controls_from_query_string():
    fields = _load_formdown_fields()
    values = _sample_form_values()
    entries = _build_query_entries(fields, values)
    query_string = urlencode(entries)
    parsed = parse_qs(query_string, keep_blank_values=True)

    excluded_names = {field["name"] for field in fields if field["type"] in EXCLUDED_TYPES}
    assert excluded_names == {"resume", "portfolio", "submit_form", "reset_form"}

    for excluded in excluded_names:
        assert excluded in values  # ensure the sample assigns a value
        assert excluded not in parsed


def test_formdown_showcase_detects_multivalue_fields():
    fields = _load_formdown_fields()
    values = _sample_form_values()
    entries = _build_query_entries(fields, values)
    query_string = urlencode(entries)
    parsed = parse_qs(query_string, keep_blank_values=True)

    assert parsed.get("skills") == ["Python", "React"]
    assert parsed.get("preferences") == ["Email Notifications", "Weekly Digest"]

