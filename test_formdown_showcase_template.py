"""Regression and characterization tests for the Formdown showcase template."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import parse_qs, urlencode


REPO_ROOT = Path(__file__).resolve().parent
FORMDOWN_SHOWCASE_PATH = (
    REPO_ROOT / "upload_templates" / "contents" / "formdown_showcase.formdown"
)


@dataclass
class FormdownField:
    """Container for a single field definition inside the showcase template."""

    name: str
    type: str
    descriptor: str
    attributes: Dict[str, str]

    @property
    def is_submission_control(self) -> bool:
        return self.type in {"submit", "reset"}

    @property
    def is_file_input(self) -> bool:
        return self.type == "file"


def _parse_descriptor(descriptor: str) -> Tuple[str, Dict[str, str]]:
    """Return the control type and attributes for the descriptor string."""

    tokens = shlex.split(descriptor)
    if not tokens:
        raise ValueError(f"Descriptor had no tokens: {descriptor!r}")

    field_type, *attribute_tokens = tokens
    attributes: Dict[str, str] = {}
    for token in attribute_tokens:
        if "=" not in token:
            attributes[token] = ""
            continue
        key, value = token.split("=", 1)
        attributes[key] = value
    return field_type, attributes


def _load_formdown_fields() -> List[FormdownField]:
    """Parse the showcase document into field metadata records."""

    document = FORMDOWN_SHOWCASE_PATH.read_text(encoding="utf-8")

    field_pattern = re.compile(
        r"^@(?P<name>[a-zA-Z0-9_]+)(?:\([^)]*\))?:\s*\[(?P<descriptor>[^\]]+)\]$",
        re.MULTILINE,
    )

    fields: List[FormdownField] = []
    for match in field_pattern.finditer(document):
        descriptor = match.group("descriptor").strip()
        field_type, attributes = _parse_descriptor(descriptor)
        fields.append(
            FormdownField(
                name=match.group("name"),
                type=field_type,
                descriptor=descriptor,
                attributes=attributes,
            )
        )
    return fields


def _sample_form_values() -> Dict[str, object]:
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
    fields: Iterable[FormdownField], values: Dict[str, object]
) -> List[Tuple[str, str]]:
    """Return (name, value) pairs that would appear in a GET query string."""

    entries: List[Tuple[str, str]] = []
    for field in fields:
        if field.type in EXCLUDED_TYPES:
            continue
        raw_value = values.get(field.name)
        if raw_value is None:
            continue
        if isinstance(raw_value, list):
            for item in raw_value:
                entries.append((field.name, str(item)))
        else:
            entries.append((field.name, str(raw_value)))
    return entries


def _fields_by_name(fields: Iterable[FormdownField]) -> Dict[str, FormdownField]:
    return {field.name: field for field in fields}


def test_formdown_showcase_fields_are_parsed_with_attributes():
    fields = _load_formdown_fields()

    assert fields, "Expected the showcase document to define multiple fields"

    field_map = _fields_by_name(fields)
    assert field_map["name"].type == "text"
    assert field_map["name"].attributes["placeholder"] == "Enter your full name"
    assert field_map["bio"].type == "textarea"
    assert field_map["bio"].attributes["placeholder"] == "Tell us about yourself"
    assert field_map["skills"].type == "checkbox"
    assert field_map["resume"].is_file_input

    checkbox_options = field_map["preferences"].attributes["options"]
    assert "Weekly Digest" in checkbox_options


def test_formdown_showcase_expected_query_serialization():
    """Document the ideal serialization behavior for GET submissions."""

    fields = _load_formdown_fields()
    values = _sample_form_values()

    entries = _build_query_entries(fields, values)
    query_string = urlencode(entries)
    parsed = parse_qs(query_string, keep_blank_values=True)

    included_fields = [field for field in fields if field.type not in EXCLUDED_TYPES]
    assert included_fields, "Expected to discover at least one included field"

    for field in included_fields:
        expected_value = values[field.name]
        actual_values = parsed.get(field.name)
        assert actual_values is not None, f"Missing {field.name} from query string"
        if isinstance(expected_value, list):
            assert actual_values == [str(item) for item in expected_value]
        else:
            assert actual_values == [str(expected_value)]


def test_formdown_showcase_excludes_non_serializable_controls():
    fields = _load_formdown_fields()
    values = _sample_form_values()

    entries = _build_query_entries(fields, values)
    query_string = urlencode(entries)
    parsed = parse_qs(query_string, keep_blank_values=True)

    excluded_names = {
        field.name for field in fields if field.is_file_input or field.is_submission_control
    }
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


# Hand-recorded from a manual submission of the showcase form where the
# "Full Name" text input and "About You" textarea were both filled with the
# literal value "Ada Lovelace" before submitting the GET form rendered by the
# Formdown UI component. Only the textarea value survives in the query string.
OBSERVED_TEXT_VS_TEXTAREA_QUERY = "bio=Ada+Lovelace"


def test_formdown_showcase_text_input_missing_from_observed_submission():
    """Regress the real-world bug where text fields drop out of the query string."""

    fields = _load_formdown_fields()
    field_map = _fields_by_name(fields)

    assert field_map["name"].type == "text"
    assert field_map["bio"].type == "textarea"

    expected_entries = _build_query_entries(fields, _sample_form_values())
    assert any(name == "name" for name, _ in expected_entries)
    assert any(name == "bio" for name, _ in expected_entries)

    observed = parse_qs(OBSERVED_TEXT_VS_TEXTAREA_QUERY, keep_blank_values=True)

    assert "bio" in observed, "Textarea value should survive the GET submission"
    assert observed["bio"] == ["Ada Lovelace"]
    assert "name" not in observed, (
        "Expected text inputs to be missing per the regression report. "
        "If this starts passing we should update the template or remove this characterization."
    )

