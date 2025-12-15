"""Import source loading and validation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from cid_presenter import format_cid
from cid_utils import generate_cid
from forms import ImportForm

from .cid_utils import normalise_cid
from .filesystem_collection import app_root_path


@dataclass
class SourceEntry:
    """Structured representation of a source file entry from the import payload."""

    raw_path: str
    relative_path: Path
    expected_cid: str


def parse_import_payload(raw_payload: str) -> tuple[ParsedImportPayload | None, str | None]:
    """Return parsed payload data or an error message if parsing fails."""
    stripped_payload = raw_payload.strip()
    if not stripped_payload:
        return None, 'Import data was empty.'

    try:
        data = json.loads(stripped_payload)
    except json.JSONDecodeError as exc:
        return None, f'Failed to parse JSON: {exc}'

    if not isinstance(data, dict):
        return None, 'Import file must contain a JSON object.'

    return ParsedImportPayload(raw_text=stripped_payload, data=data), None


@dataclass
class ParsedImportPayload:
    """Parsed import payload data."""

    raw_text: str
    data: dict[str, Any]


def load_import_payload(form: ImportForm) -> str | None:
    """Return JSON content based on the selected import source."""
    source = form.import_source.data

    if source == 'file':
        file_storage = form.import_file.data
        if not file_storage:
            form.import_file.errors.append('Choose a JSON file to upload.')
            return None
        try:
            raw_bytes = file_storage.read()
        except RuntimeError:
            form.import_file.errors.append('Unable to read the uploaded file.')
            return None
        if not raw_bytes:
            form.import_file.errors.append('Uploaded file was empty.')
            return None
        try:
            return raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            form.import_file.errors.append('Uploaded file must be UTF-8 encoded JSON.')
            return None

    if source == 'text':
        return form.import_text.data.strip()

    if source == 'url':
        url = form.import_url.data.strip()
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.RequestException:
            form.import_url.errors.append('Failed to download JSON from the provided URL.')
            return None
        if not response.text.strip():
            form.import_url.errors.append('Downloaded file was empty.')
            return None
        return response.text

    if source == 'github_pr':
        from .github_pr import fetch_pr_export_data
        
        pr_url = form.github_pr_url.data.strip() if form.github_pr_url.data else ''
        if not pr_url:
            form.github_pr_url.errors.append('GitHub PR URL is required.')
            return None
        
        github_token = form.github_import_token.data.strip() if form.github_import_token.data else None
        
        json_data, error_message = fetch_pr_export_data(pr_url, github_token)
        if error_message:
            form.github_pr_url.errors.append(error_message)
            return None
        
        return json_data

    return None


def parse_source_entry(entry: Any, label_text: str, warnings: list[str]) -> SourceEntry | None:
    """Return a parsed source entry when the structure is valid."""
    if not isinstance(entry, dict):
        warnings.append(f'{label_text} entry must include "path" and "cid" fields.')
        return None

    raw_path = entry.get('path')
    expected_cid = normalise_cid(entry.get('cid'))
    if not isinstance(raw_path, str) or not expected_cid:
        warnings.append(f'{label_text} entry must include valid "path" and "cid" values.')
        return None

    candidate_path = Path(raw_path)
    if candidate_path.is_absolute() or '..' in candidate_path.parts:
        warnings.append(f'Source file "{raw_path}" used an invalid path.')
        return None

    return SourceEntry(raw_path=raw_path, relative_path=candidate_path, expected_cid=expected_cid)


def resolve_source_entry(
    entry: SourceEntry,
    base_path: Path,
    base_resolved: Path,
    warnings: list[str],
) -> Path | None:
    """Return the absolute path for a parsed source entry if it exists locally."""
    absolute_path = (base_path / entry.relative_path).resolve()
    try:
        absolute_path.relative_to(base_resolved)
    except ValueError:
        warnings.append(f'Source file "{entry.raw_path}" used an invalid path.')
        return None

    if not absolute_path.exists():
        warnings.append(f'Source file "{entry.raw_path}" is missing locally.')
        return None

    if not absolute_path.is_file():
        warnings.append(f'Source path "{entry.raw_path}" is not a file locally.')
        return None

    return absolute_path


def load_source_entry_bytes(
    absolute_path: Path,
    entry: SourceEntry,
    warnings: list[str],
) -> bytes | None:
    """Return the byte content of an import source entry if readable."""
    try:
        return absolute_path.read_bytes()
    except OSError:
        warnings.append(f'Source file "{entry.raw_path}" could not be read locally.')
        return None


def source_entry_matches_export(entry: SourceEntry, local_bytes: bytes, warnings: list[str]) -> bool:
    """Return True when the local file content matches the export metadata."""
    local_cid = format_cid(generate_cid(local_bytes))
    if normalise_cid(entry.expected_cid) != local_cid:
        warnings.append(f'Source file "{entry.raw_path}" differs from the export.')
        return False
    return True


def verify_import_source_category(
    entries: Any,
    label_text: str,
    warnings: list[str],
    info_messages: list[str],
) -> None:
    """Verify source files for a specific category."""
    lower_label = label_text.lower()

    if entries is None:
        warnings.append(f'No {lower_label} were included in the import data.')
        return

    if not isinstance(entries, list):
        warnings.append(f'{label_text} section must be a list of file entries.')
        return

    base_path = app_root_path()
    base_resolved = base_path.resolve()
    checked_any = False
    mismatches_found = False

    for raw_entry in entries:
        parsed_entry = parse_source_entry(raw_entry, label_text, warnings)
        if parsed_entry is None:
            mismatches_found = True
            continue

        absolute_path = resolve_source_entry(parsed_entry, base_path, base_resolved, warnings)
        if absolute_path is None:
            mismatches_found = True
            continue

        checked_any = True
        content = load_source_entry_bytes(absolute_path, parsed_entry, warnings)
        if content is None:
            mismatches_found = True
            continue

        if not source_entry_matches_export(parsed_entry, content, warnings):
            mismatches_found = True

    if checked_any and not mismatches_found:
        info_messages.append(f'All {lower_label} match the export.')
    elif not checked_any:
        warnings.append(f'No valid {lower_label} were found in the import data.')


def verify_import_source_files(
    raw_section: Any,
    selected_categories: list[tuple[str, str]],
    warnings: list[str],
    info_messages: list[str],
) -> None:
    """Verify all selected source file categories."""
    if not selected_categories:
        return

    if raw_section is None:
        for _, label_text in selected_categories:
            warnings.append(f'No {label_text.lower()} were included in the import data.')
        return

    if not isinstance(raw_section, dict):
        warnings.append('App source files section must be an object mapping categories to file entries.')
        return

    for category_key, label_text in selected_categories:
        entries = raw_section.get(category_key)
        verify_import_source_category(entries, label_text, warnings, info_messages)
