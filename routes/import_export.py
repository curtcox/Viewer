"""Routes for exporting and importing user configuration data."""
from __future__ import annotations

import base64
import binascii
import json
import platform
import re
import sys
import tomllib
from datetime import datetime, timezone
from importlib import metadata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional, Tuple

import requests
from flask import current_app, flash, redirect, render_template, request, url_for

from alias_definition import (
    AliasDefinitionError,
    format_primary_alias_line,
    parse_alias_definition,
    replace_primary_definition_line,
)
from cid_presenter import cid_path, format_cid
from cid_utils import (
    generate_cid,
    save_server_definition_as_cid,
    store_cid_from_bytes,
)
from db_access import (
    EntityInteractionLookup,
    EntityInteractionRequest,
    find_entity_interaction,
    get_alias_by_name,
    get_cid_by_path,
    get_entity_interactions,
    get_secret_by_name,
    get_server_by_name,
    get_user_aliases,
    get_user_exports,
    get_user_secrets,
    get_user_servers,
    get_user_uploads,
    get_user_variables,
    get_variable_by_name,
    record_entity_interaction,
    record_export,
    save_entity,
)
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from forms import ExportForm, ImportForm
from wtforms import SelectMultipleField
from identity import current_user
from interaction_log import load_interaction_history
from models import Alias, Secret, Server, Variable

from . import main_bp
from .core import get_existing_routes
from .secrets import update_secret_definitions_cid
from .servers import update_server_definitions_cid
from .variables import update_variable_definitions_cid


_SELECTION_SENTINEL = '__none__'


def _normalise_cid(value: Any) -> str:
    if not isinstance(value, str):
        return ''
    cleaned = value.strip()
    if not cleaned:
        return ''
    cleaned = cleaned.split('.')[0]
    return cleaned.lstrip('/')


def _coerce_enabled_flag(value: Any) -> bool:
    """Return a best-effort boolean for enabled flags in import payloads."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'false', '0', 'off', 'no'}:
            return False
        if normalized in {'true', '1', 'on', 'yes'}:
            return True

    if isinstance(value, (int, float)):
        return bool(value)

    return True if value is None else bool(value)


def _serialise_cid_value(content: bytes) -> str:
    """Serialize CID content as a UTF-8 string for export.

    Always decodes content as UTF-8. If the content contains invalid UTF-8
    sequences, they are replaced with the Unicode replacement character.
    """
    return content.decode('utf-8', errors='replace')


def _format_size(num_bytes: int) -> str:
    units = ['bytes', 'KB', 'MB', 'GB', 'TB']
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'bytes':
                return f'{int(size)} bytes'
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{int(num_bytes)} bytes'


@dataclass
class _CidWriter:
    user_id: str
    include_optional: bool
    store_content: bool
    cid_map_entries: dict[str, str] = field(default_factory=dict)

    def cid_for_content(
        self,
        content: bytes,
        *,
        optional: bool = True,
        include_in_map: bool = True,
    ) -> str:
        if self.store_content:
            cid_value = store_cid_from_bytes(content, self.user_id)
        else:
            cid_value = format_cid(generate_cid(content))

        if include_in_map:
            _store_cid_entry(
                cid_value,
                content,
                self.cid_map_entries,
                self.include_optional,
                optional=optional,
            )

        return cid_value


def _deserialise_cid_value(raw_value: Any) -> tuple[bytes | None, str | None]:
    if isinstance(raw_value, dict):
        encoding = (raw_value.get('encoding') or 'utf-8').strip().lower()
        value = raw_value.get('value')
    else:
        encoding = 'utf-8'
        value = raw_value

    if not isinstance(value, str):
        return None, 'CID map values must be strings or objects with a "value" field.'

    if encoding in ('utf-8', 'text', 'utf8'):
        return value.encode('utf-8'), None

    if encoding == 'base64':
        try:
            return base64.b64decode(value.encode('ascii')), None
        except (binascii.Error, ValueError):
            return None, 'CID map entry used invalid base64 encoding.'

    try:
        return value.encode(encoding), None
    except LookupError:
        return None, f'CID map entry specified unsupported encoding "{encoding}".'


def _parse_cid_values_section(raw_map: Any) -> tuple[dict[str, bytes], list[str]]:
    if raw_map is None:
        return {}, []
    if not isinstance(raw_map, dict):
        return {}, ['CID map must be an object mapping CID values to content.']

    cid_values: dict[str, bytes] = {}
    errors: list[str] = []

    for raw_key, raw_value in raw_map.items():
        cid_value = _normalise_cid(raw_key)
        if not cid_value:
            errors.append('CID map entries must use non-empty string keys.')
            continue

        content_bytes, error = _deserialise_cid_value(raw_value)
        if error:
            errors.append(f'CID "{cid_value}" entry invalid: {error}')
            continue
        if content_bytes is None:
            errors.append(f'CID "{cid_value}" entry did not include decodable content.')
            continue

        cid_values[cid_value] = content_bytes

    return cid_values, errors


def _load_cid_bytes(cid_value: str, cid_map: dict[str, bytes]) -> bytes | None:
    normalised = _normalise_cid(cid_value)
    if not normalised:
        return None

    if normalised in cid_map:
        return cid_map[normalised]

    path = cid_path(normalised)
    if not path:
        return None

    record = get_cid_by_path(path)
    if record and record.file_data is not None:
        return bytes(record.file_data)

    return None


def _encode_section_content(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode('utf-8')


def _load_export_section(
    payload: dict[str, Any],
    key: str,
    cid_map: dict[str, bytes],
) -> tuple[Any, list[str], bool]:
    if key not in payload:
        return None, [], False

    raw_value = payload.get(key)
    if isinstance(raw_value, str):
        cid_value = _normalise_cid(raw_value)
        if not cid_value:
            return None, [f'Section "{key}" referenced an invalid CID value.'], True
        content_bytes = _load_cid_bytes(cid_value, cid_map)
        if content_bytes is None:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" but the content was not provided.'
            ], True
        try:
            decoded_text = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" that was not UTF-8 encoded.'
            ], True
        try:
            return json.loads(decoded_text), [], False
        except json.JSONDecodeError:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" with invalid JSON content.'
            ], True

    return raw_value, [], False


_APP_SOURCE_TEMPLATE_DIRECTORIES: tuple[str, ...] = (
    'templates',
    'server_templates',
    'upload_templates',
)

_APP_SOURCE_STATIC_DIRECTORIES: tuple[str, ...] = ('static',)

_APP_SOURCE_OTHER_FILES: tuple[Path, ...] = (
    Path('pyproject.toml'),
    Path('requirements.txt'),
    Path('uv.lock'),
    Path('.env.sample'),
    Path('run'),
    Path('install'),
    Path('doctor'),
    Path('README.md'),
    Path('replit.md'),
)

_PYTHON_SOURCE_EXCLUDED_DIRS: set[str] = {'test', 'tests', '__pycache__', 'venv', '.venv'}
_PYTHON_SOURCE_EXCLUDED_FILENAMES: set[str] = {'run_coverage.py', 'run_auth_tests.py'}

_APP_SOURCE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ('python', 'Python Source Files'),
    ('templates', 'Templates'),
    ('static', 'Static Files'),
    ('other', 'Other App Files'),
)


def _app_root_path() -> Path:
    return Path(current_app.root_path)


def _should_include_python_source(relative_path: Path) -> bool:
    if relative_path.suffix != '.py':
        return False

    if any(part in _PYTHON_SOURCE_EXCLUDED_DIRS for part in relative_path.parts):
        return False

    if relative_path.name.startswith('test_'):
        return False

    if relative_path.name in _PYTHON_SOURCE_EXCLUDED_FILENAMES:
        return False

    return True


def _gather_python_source_paths() -> list[Path]:
    base_path = _app_root_path()
    python_files: list[Path] = []

    for path in base_path.rglob('*.py'):
        try:
            relative_path = path.relative_to(base_path)
        except ValueError:
            continue

        if _should_include_python_source(relative_path):
            python_files.append(relative_path)

    python_files.sort(key=lambda item: item.as_posix())
    return python_files


def _gather_files_from_directories(relative_directories: Iterable[str]) -> list[Path]:
    base_path = _app_root_path()
    collected: list[Path] = []

    for relative in relative_directories:
        directory_path = base_path / relative
        if not directory_path.exists() or not directory_path.is_dir():
            continue

        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                collected.append(file_path.relative_to(base_path))

    collected.sort(key=lambda item: item.as_posix())
    return collected


def _gather_template_paths() -> list[Path]:
    return _gather_files_from_directories(_APP_SOURCE_TEMPLATE_DIRECTORIES)


def _gather_static_paths() -> list[Path]:
    return _gather_files_from_directories(_APP_SOURCE_STATIC_DIRECTORIES)


def _gather_other_app_files() -> list[Path]:
    base_path = _app_root_path()
    other_files: list[Path] = []

    for relative in _APP_SOURCE_OTHER_FILES:
        candidate = base_path / relative
        if candidate.exists() and candidate.is_file():
            other_files.append(relative)

    other_files.sort(key=lambda item: item.as_posix())
    return other_files


_APP_SOURCE_COLLECTORS: dict[str, Callable[[], list[Path]]] = {
    'python': _gather_python_source_paths,
    'templates': _gather_template_paths,
    'static': _gather_static_paths,
    'other': _gather_other_app_files,
}


_REQUIREMENT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*')


def _parse_dependency_name(raw_value: Any) -> str | None:
    if not isinstance(raw_value, str):
        return None

    text = raw_value.strip()
    if not text or text.startswith('#'):
        return None

    for prefix in ('-e ', '--', 'git+', 'http://', 'https://'):
        if text.startswith(prefix):
            return None

    text = text.split(';', 1)[0].strip()
    bracket_index = text.find('[')
    if bracket_index != -1:
        text = text[:bracket_index]

    for separator in ('===', '==', '>=', '<=', '!=', '~=', '>', '<'):
        if separator in text:
            text = text.split(separator, 1)[0]
            break

    match = _REQUIREMENT_NAME_PATTERN.match(text)
    if not match:
        return None

    return match.group(0).lower()


def _collect_project_dependencies() -> set[str]:
    base_path = _app_root_path()
    dependency_names: set[str] = set()

    pyproject_path = base_path / 'pyproject.toml'
    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text('utf-8'))
        except (OSError, tomllib.TOMLDecodeError):
            data = None
        if isinstance(data, dict):
            project_section = data.get('project')
            if isinstance(project_section, dict):
                raw_dependencies = project_section.get('dependencies', [])
                if isinstance(raw_dependencies, list):
                    for entry in raw_dependencies:
                        name = _parse_dependency_name(entry)
                        if name:
                            dependency_names.add(name)

    requirements_path = base_path / 'requirements.txt'
    if requirements_path.exists():
        try:
            raw_requirements = requirements_path.read_text('utf-8').splitlines()
        except OSError:
            raw_requirements = []
        for entry in raw_requirements:
            name = _parse_dependency_name(entry)
            if name:
                dependency_names.add(name)

    return dependency_names


def _gather_dependency_versions() -> dict[str, dict[str, str]]:
    dependency_versions: dict[str, dict[str, str]] = {}

    for name in sorted(_collect_project_dependencies(), key=lambda item: item.lower()):
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        dependency_versions[name] = {'version': version}

    return dependency_versions


def _build_runtime_section() -> dict[str, dict[str, str]]:
    return {
        'python': {
            'implementation': platform.python_implementation(),
            'version': platform.python_version(),
            'executable': sys.executable or '',
        },
        'dependencies': _gather_dependency_versions(),
    }


@dataclass
class _SourceEntry:
    """Structured representation of a source file entry from the import payload."""

    raw_path: str
    relative_path: Path
    expected_cid: str


@dataclass
class _AliasImport:
    """Normalized alias entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool
    template: bool


def _prepare_alias_import(
    entry: Any,
    reserved_routes: set[str],
    cid_map: dict[str, bytes],
    errors: list[str],
) -> _AliasImport | None:
    """Return a normalized alias import entry when the payload entry is valid."""

    if not isinstance(entry, dict):
        errors.append('Alias entries must be objects with name and definition details.')
        return None

    name_raw = entry.get('name')
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append('Alias entry must include a valid name.')
        return None

    name = name_raw.strip()

    if f'/{name}' in reserved_routes:
        errors.append(f'Alias "{name}" conflicts with an existing route and was skipped.')
        return None

    definition_text: Optional[str] = None
    raw_definition = entry.get('definition')
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Alias "{name}" definition must be text when provided.')
        return None

    definition_cid = _normalise_cid(entry.get('definition_cid'))

    if definition_text is None and definition_cid:
        cid_bytes = _load_cid_bytes(definition_cid, cid_map)
        if cid_bytes is None:
            errors.append(
                f'Alias "{name}" definition with CID "{definition_cid}" was not included in the import.'
            )
            return None
        try:
            definition_text = cid_bytes.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(
                f'Alias "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
            )
            return None

    if definition_text is None:
        errors.append(f'Alias "{name}" entry must include either a definition or a definition_cid.')
        return None

    try:
        parsed_definition = parse_alias_definition(definition_text, alias_name=name)
    except AliasDefinitionError as exc:
        errors.append(f'Alias "{name}" definition could not be parsed: {exc}')
        return None

    canonical_primary = format_primary_alias_line(
        parsed_definition.match_type,
        parsed_definition.match_pattern,
        parsed_definition.target_path,
        ignore_case=parsed_definition.ignore_case,
        alias_name=name,
    )
    definition_value = replace_primary_definition_line(
        definition_text,
        canonical_primary,
    )

    enabled = _coerce_enabled_flag(entry.get('enabled'))
    template = _coerce_enabled_flag(entry.get('template'))

    return _AliasImport(
        name=name,
        definition=definition_value,
        enabled=enabled,
        template=template,
    )


def _parse_source_entry(entry: Any, label_text: str, warnings: list[str]) -> _SourceEntry | None:
    """Return a parsed source entry when the structure is valid."""

    if not isinstance(entry, dict):
        warnings.append(f'{label_text} entry must include "path" and "cid" fields.')
        return None

    raw_path = entry.get('path')
    expected_cid = _normalise_cid(entry.get('cid'))
    if not isinstance(raw_path, str) or not expected_cid:
        warnings.append(f'{label_text} entry must include valid "path" and "cid" values.')
        return None

    candidate_path = Path(raw_path)
    if candidate_path.is_absolute() or '..' in candidate_path.parts:
        warnings.append(f'Source file "{raw_path}" used an invalid path.')
        return None

    return _SourceEntry(raw_path=raw_path, relative_path=candidate_path, expected_cid=expected_cid)


def _resolve_source_entry(
    entry: _SourceEntry,
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


def _load_source_entry_bytes(
    absolute_path: Path,
    entry: _SourceEntry,
    warnings: list[str],
) -> bytes | None:
    """Return the byte content of an import source entry if readable."""

    try:
        return absolute_path.read_bytes()
    except OSError:
        warnings.append(f'Source file "{entry.raw_path}" could not be read locally.')
        return None


def _source_entry_matches_export(entry: _SourceEntry, local_bytes: bytes, warnings: list[str]) -> bool:
    """Return True when the local file content matches the export metadata."""

    local_cid = format_cid(generate_cid(local_bytes))
    if _normalise_cid(entry.expected_cid) != local_cid:
        warnings.append(f'Source file "{entry.raw_path}" differs from the export.')
        return False
    return True


def _store_cid_entry(
    cid_value: str,
    content: bytes,
    cid_map_entries: dict[str, str],
    include_optional: bool,
    *,
    optional: bool = True,
) -> None:
    """Record a CID value for the export when it should be included."""

    if optional and not include_optional:
        return

    normalised = _normalise_cid(cid_value)
    if not normalised or normalised in cid_map_entries:
        return

    cid_map_entries[normalised] = _serialise_cid_value(content)


def _collect_project_files_section(
    base_path: Path,
    cid_writer: _CidWriter,
) -> dict[str, dict[str, str]]:
    """Return CID metadata for key project files when available."""

    project_files_payload: dict[str, dict[str, str]] = {}
    for relative_name in ('pyproject.toml', 'requirements.txt'):
        absolute_path = base_path / relative_name
        try:
            file_content = absolute_path.read_bytes()
        except OSError:
            continue

        cid_value = cid_writer.cid_for_content(file_content)
        project_files_payload[relative_name] = {'cid': cid_value}

    return project_files_payload


def _should_export_entry(
    enabled: bool,
    template: bool,
    *,
    include_disabled: bool,
    include_templates: bool,
) -> bool:
    """Return True when the entry should be included in the export."""

    if template:
        if not include_templates:
            return False
        return True

    if not enabled:
        return include_disabled

    return True


def _preview_item_entries(records: Iterable[Any]) -> list[dict[str, Any]]:
    """Return serialisable preview entries for export-capable records."""

    entries: list[dict[str, Any]] = []
    for record in records:
        name = getattr(record, 'name', '') or ''
        enabled = bool(getattr(record, 'enabled', True))
        template = bool(getattr(record, 'template', False))
        entries.append({'name': name, 'enabled': enabled, 'template': template})

    entries.sort(key=lambda entry: entry['name'].casefold())
    return entries


def _selected_name_set(raw_values: Iterable[Any]) -> set[str]:
    """Return a cleaned set of user-selected entry names."""

    selected: set[str] = set()
    for value in raw_values or []:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned == _SELECTION_SENTINEL:
            continue
        selected.add(cleaned)

    return selected


def _filter_preview_items(
    items: Iterable[dict[str, Any]],
    *,
    include_disabled: bool,
    include_templates: bool,
) -> list[dict[str, Any]]:
    """Return preview entries that satisfy the current export filters."""

    filtered: list[dict[str, Any]] = []
    for item in items:
        enabled = bool(item.get('enabled', True))
        template = bool(item.get('template', False))

        if not _should_export_entry(
            enabled,
            template,
            include_disabled=include_disabled,
            include_templates=include_templates,
        ):
            continue

        filtered.append(item)

    return filtered


def _build_export_preview(form: ExportForm, user_id: str) -> dict[str, dict[str, Any]]:
    """Return metadata describing which items are currently selected for export."""

    def _initialise_selection(
        field: SelectMultipleField,
        entries: list[dict[str, Any]],
    ) -> set[str]:
        available_names: list[str] = []
        for entry in entries:
            name = entry.get('name')
            if not isinstance(name, str):
                continue
            cleaned = name.strip()
            if not cleaned:
                continue
            available_names.append(cleaned)

        field.choices = [(name, name) for name in available_names]

        raw_data = list(field.raw_data or [])
        submitted = bool(raw_data)
        cleaned_values: list[str] = []
        for value in field.data or []:
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if not cleaned or cleaned == _SELECTION_SENTINEL:
                continue
            cleaned_values.append(cleaned)

        if not submitted:
            cleaned_values = list(available_names)

        field.data = cleaned_values
        return set(cleaned_values)

    def _build_section(
        entries: list[dict[str, Any]],
        include_collection: bool,
        include_disabled: bool,
        include_templates: bool,
        label: str,
        field: SelectMultipleField,
    ) -> dict[str, Any]:
        capitalised_label = label.title()
        selected_names = _initialise_selection(field, entries)
        filtered_items = (
            _filter_preview_items(
                entries,
                include_disabled=include_disabled,
                include_templates=include_templates,
            )
            if include_collection
            else []
        )
        filtered_names = {
            item.get('name')
            for item in filtered_items
            if isinstance(item.get('name'), str) and item.get('name')
        }

        return {
            'label': label,
            'include': include_collection,
            'available': entries,
            'selected': filtered_items,
            'selected_names': sorted(selected_names & filtered_names, key=str.casefold),
            'known_names': sorted(filtered_names, key=str.casefold),
            'field_name': field.name,
            'selection_sentinel': _SELECTION_SENTINEL,
            'empty_message': f'No {label} available for export.',
            'not_selected_message': f'{capitalised_label} are not selected for export.',
        }

    alias_entries = _preview_item_entries(get_user_aliases(user_id))
    server_entries = _preview_item_entries(get_user_servers(user_id))
    variable_entries = _preview_item_entries(get_user_variables(user_id))
    secret_entries = _preview_item_entries(get_user_secrets(user_id))

    return {
        'aliases': _build_section(
            alias_entries,
            bool(form.include_aliases.data),
            bool(form.include_disabled_aliases.data),
            bool(form.include_template_aliases.data),
            'aliases',
            form.selected_aliases,
        ),
        'servers': _build_section(
            server_entries,
            bool(form.include_servers.data),
            bool(form.include_disabled_servers.data),
            bool(form.include_template_servers.data),
            'servers',
            form.selected_servers,
        ),
        'variables': _build_section(
            variable_entries,
            bool(form.include_variables.data),
            bool(form.include_disabled_variables.data),
            bool(form.include_template_variables.data),
            'variables',
            form.selected_variables,
        ),
        'secrets': _build_section(
            secret_entries,
            bool(form.include_secrets.data),
            bool(form.include_disabled_secrets.data),
            bool(form.include_template_secrets.data),
            'secrets',
            form.selected_secrets,
        ),
    }


def _collect_alias_section(
    form: ExportForm,
    user_id: str,
    cid_writer: _CidWriter,
) -> list[dict[str, Any]]:
    """Return alias export entries including CID references."""

    aliases = list(get_user_aliases(user_id))
    selected_names = _selected_name_set(form.selected_aliases.data)
    if not selected_names and not getattr(form.selected_aliases, 'raw_data', None):
        selected_names = {
            alias.name
            for alias in aliases
            if isinstance(getattr(alias, 'name', None), str) and alias.name
        }
    alias_payload: list[dict[str, Any]] = []
    for alias in aliases:
        name = getattr(alias, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        definition_text = alias.definition or ''
        definition_bytes = definition_text.encode('utf-8')
        definition_cid = cid_writer.cid_for_content(definition_bytes)
        enabled = bool(getattr(alias, 'enabled', True))
        template = bool(getattr(alias, 'template', False))

        if not _should_export_entry(
            enabled,
            template,
            include_disabled=form.include_disabled_aliases.data,
            include_templates=form.include_template_aliases.data,
        ):
            continue

        alias_payload.append(
            {
                'name': name,
                'definition_cid': definition_cid,
                'enabled': enabled,
                'template': template,
            }
        )

    return alias_payload


def _collect_server_section(
    form: ExportForm,
    user_id: str,
    cid_writer: _CidWriter,
) -> list[dict[str, str]]:
    """Return server export entries including CID references."""

    servers = list(get_user_servers(user_id))
    selected_names = _selected_name_set(form.selected_servers.data)
    if not selected_names and not getattr(form.selected_servers, 'raw_data', None):
        selected_names = {
            server.name
            for server in servers
            if isinstance(getattr(server, 'name', None), str) and server.name
        }
    servers_payload: list[dict[str, str]] = []
    for server in servers:
        name = getattr(server, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        definition_text = server.definition or ''
        definition_bytes = definition_text.encode('utf-8')
        definition_cid = cid_writer.cid_for_content(definition_bytes)
        enabled = bool(getattr(server, 'enabled', True))
        template = bool(getattr(server, 'template', False))

        if not _should_export_entry(
            enabled,
            template,
            include_disabled=form.include_disabled_servers.data,
            include_templates=form.include_template_servers.data,
        ):
            continue

        servers_payload.append(
            {
                'name': name,
                'definition_cid': definition_cid,
                'enabled': enabled,
                'template': template,
            }
        )

    return servers_payload


def _collect_variables_section(form: ExportForm, user_id: str) -> list[dict[str, str]]:
    """Return variable export entries for the user."""

    variables = list(get_user_variables(user_id))
    selected_names = _selected_name_set(form.selected_variables.data)
    if not selected_names and not getattr(form.selected_variables, 'raw_data', None):
        selected_names = {
            variable.name
            for variable in variables
            if isinstance(getattr(variable, 'name', None), str) and variable.name
        }
    variable_payload: list[dict[str, str]] = []
    for variable in variables:
        name = getattr(variable, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        enabled = bool(getattr(variable, 'enabled', True))
        template = bool(getattr(variable, 'template', False))

        if not _should_export_entry(
            enabled,
            template,
            include_disabled=form.include_disabled_variables.data,
            include_templates=form.include_template_variables.data,
        ):
            continue

        variable_payload.append(
            {
                'name': name,
                'definition': variable.definition,
                'enabled': enabled,
                'template': template,
            }
        )

    return variable_payload


def _collect_secrets_section(
    form: ExportForm,
    user_id: str,
    key: str,
    include_disabled: bool,
    include_templates: bool,
) -> dict[str, Any]:
    """Return encrypted secret entries using the provided key."""

    secrets = list(get_user_secrets(user_id))
    selected_names = _selected_name_set(form.selected_secrets.data)
    if not selected_names and not getattr(form.selected_secrets, 'raw_data', None):
        selected_names = {
            secret.name
            for secret in secrets
            if isinstance(getattr(secret, 'name', None), str) and secret.name
        }
    items: list[dict[str, Any]] = []
    for secret in secrets:
        name = getattr(secret, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        enabled = bool(getattr(secret, 'enabled', True))
        template = bool(getattr(secret, 'template', False))

        if not _should_export_entry(
            enabled,
            template,
            include_disabled=include_disabled,
            include_templates=include_templates,
        ):
            continue

        items.append(
            {
                'name': name,
                'ciphertext': encrypt_secret_value(secret.definition, key),
                'enabled': enabled,
                'template': template,
            }
        )

    return {
        'encryption': SECRET_ENCRYPTION_SCHEME,
        'items': items,
    }


def _collect_history_section(user_id: str) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Return change history grouped by collection when available."""

    history_payload = _gather_change_history(user_id)
    return history_payload if history_payload else {}


def _collect_app_source_section(
    form: ExportForm,
    base_path: Path,
    cid_writer: _CidWriter,
) -> dict[str, list[dict[str, str]]]:
    """Return exported application source entries based on the selected categories."""

    app_source_payload: dict[str, list[dict[str, str]]] = {}
    for category, _label in _APP_SOURCE_CATEGORIES:
        collector = _APP_SOURCE_COLLECTORS.get(category)
        if not collector:
            continue

        entries: list[dict[str, str]] = []
        for relative_path in collector():
            absolute_path = base_path / relative_path
            try:
                content_bytes = absolute_path.read_bytes()
            except OSError:
                continue

            cid_value = cid_writer.cid_for_content(content_bytes)
            entries.append({'path': relative_path.as_posix(), 'cid': cid_value})

        if entries:
            app_source_payload[category] = entries

    return app_source_payload


def _include_unreferenced_cids(
    form: ExportForm,
    user_id: str,
    cid_map_entries: dict[str, str],
) -> None:
    """Record uploaded CID content when the user requests unreferenced data."""

    if not form.include_cid_map.data or not form.include_unreferenced_cid_data.data:
        return

    for record in get_user_uploads(user_id):
        normalised = _normalise_cid(record.path)
        if not normalised or normalised in cid_map_entries:
            continue
        file_content = record.file_data
        if file_content is None:
            continue
        cid_map_entries[normalised] = _serialise_cid_value(bytes(file_content))


def _add_optional_section(
    sections: dict[str, Any],
    include_section: bool,
    section_key: str,
    builder: Callable[[], Any],
    *,
    require_truthy: bool = True,
) -> None:
    """Conditionally add an export section produced by a builder callback."""

    if not include_section:
        return

    section_value = builder()
    if section_value or not require_truthy:
        sections[section_key] = section_value


def _build_export_payload(
    form: ExportForm,
    user_id: str,
    *,
    store_content: bool = True,
) -> dict[str, Any]:
    """Return rendered export payload data for the user's selected collections."""

    payload: dict[str, Any] = {'version': 6}
    sections: dict[str, Any] = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'runtime': _build_runtime_section(),
    }
    base_path = _app_root_path()
    cid_writer = _CidWriter(
        user_id=user_id,
        include_optional=form.include_cid_map.data,
        store_content=store_content,
    )

    _add_optional_section(
        sections,
        True,
        'project_files',
        lambda: _collect_project_files_section(base_path, cid_writer),
    )

    _add_optional_section(
        sections,
        form.include_aliases.data,
        'aliases',
        lambda: _collect_alias_section(form, user_id, cid_writer),
    )

    _add_optional_section(
        sections,
        form.include_servers.data,
        'servers',
        lambda: _collect_server_section(form, user_id, cid_writer),
    )

    _add_optional_section(
        sections,
        form.include_variables.data,
        'variables',
        lambda: _collect_variables_section(form, user_id),
        require_truthy=False,
    )

    _add_optional_section(
        sections,
        form.include_secrets.data,
        'secrets',
        lambda: _collect_secrets_section(
            form,
            user_id,
            form.secret_key.data.strip(),
            form.include_disabled_secrets.data,
            form.include_template_secrets.data,
        ),
        require_truthy=False,
    )

    _add_optional_section(
        sections,
        form.include_history.data,
        'change_history',
        lambda: _collect_history_section(user_id),
    )

    _add_optional_section(
        sections,
        form.include_source.data,
        'app_source',
        lambda: _collect_app_source_section(form, base_path, cid_writer),
    )

    _include_unreferenced_cids(form, user_id, cid_writer.cid_map_entries)

    for section_name, section_value in sections.items():
        section_bytes = _encode_section_content(section_value)
        section_cid = cid_writer.cid_for_content(section_bytes, optional=False)
        payload[section_name] = section_cid

    if form.include_cid_map.data and cid_writer.cid_map_entries:
        payload['cid_values'] = {
            cid: cid_writer.cid_map_entries[cid] for cid in sorted(cid_writer.cid_map_entries)
        }

    ordered_keys = sorted(key for key in payload if key != 'cid_values')
    if 'cid_values' in payload:
        ordered_keys.append('cid_values')

    ordered_payload = {key: payload[key] for key in ordered_keys}
    json_payload = json.dumps(ordered_payload, indent=2)
    json_bytes = json_payload.encode('utf-8')

    if store_content:
        cid_value = cid_writer.cid_for_content(json_bytes, optional=False, include_in_map=False)
        download_path = cid_path(cid_value, 'json') or ''
    else:
        cid_value = format_cid(generate_cid(json_bytes))
        download_path = ''

    return {
        'cid_value': cid_value,
        'download_path': download_path,
        'json_payload': json_payload,
    }


def _import_section(context: _ImportContext, plan: _SectionImportPlan) -> int:
    """Load and import a selected export section if requested."""

    if not plan.include:
        return 0

    section, load_errors, fatal = _load_export_section(
        context.data,
        plan.section_key,
        context.cid_lookup,
    )
    context.errors.extend(load_errors)
    if fatal:
        return 0

    imported_count, import_errors = plan.importer(section)
    context.errors.extend(import_errors)
    if imported_count:
        label = plan.plural_label if imported_count != 1 else plan.singular_label
        context.summaries.append(f'{imported_count} {label}')

    return imported_count


@dataclass
class _ParsedImportPayload:
    raw_text: str
    data: dict[str, Any]


@dataclass
class _ImportContext:
    form: ImportForm
    user_id: str
    change_message: str
    raw_payload: str
    data: dict[str, Any]
    cid_lookup: dict[str, bytes] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    secret_key: str = ''
    snapshot_export: dict[str, Any] | None = None


@dataclass(frozen=True)
class _SectionImportPlan:
    include: bool
    section_key: str
    importer: Callable[[Any], Tuple[int, list[str]]]
    singular_label: str
    plural_label: str


def _parse_import_payload(raw_payload: str) -> tuple[_ParsedImportPayload | None, str | None]:
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

    return _ParsedImportPayload(raw_text=stripped_payload, data=data), None


def _create_import_context(
    form: ImportForm,
    change_message: str,
    parsed_payload: _ParsedImportPayload,
) -> _ImportContext:
    secret_key = (form.secret_key.data or '').strip()
    return _ImportContext(
        form=form,
        user_id=current_user.id,
        change_message=change_message,
        raw_payload=parsed_payload.raw_text,
        data=parsed_payload.data,
        secret_key=secret_key,
    )


def _ingest_import_cid_map(context: _ImportContext) -> None:
    parsed_cids, cid_map_errors = _parse_cid_values_section(context.data.get('cid_values'))
    context.errors.extend(cid_map_errors)

    for cid_value, content_bytes in parsed_cids.items():
        expected_cid = _normalise_cid(format_cid(generate_cid(content_bytes)))
        if expected_cid and cid_value != expected_cid:
            context.errors.append(
                f'CID "{cid_value}" content did not match its hash and was skipped.'
            )
            continue
        context.cid_lookup[cid_value] = content_bytes
        if context.form.process_cid_map.data:
            store_cid_from_bytes(content_bytes, context.user_id)


def _import_selected_sections(context: _ImportContext) -> None:
    section_importers: Iterable[_SectionImportPlan] = [
        _SectionImportPlan(
            include=context.form.include_aliases.data,
            section_key='aliases',
            importer=lambda section: _import_aliases(
                context.user_id, section, context.cid_lookup
            ),
            singular_label='alias',
            plural_label='aliases',
        ),
        _SectionImportPlan(
            include=context.form.include_servers.data,
            section_key='servers',
            importer=lambda section: _import_servers(
                context.user_id, section, context.cid_lookup
            ),
            singular_label='server',
            plural_label='servers',
        ),
        _SectionImportPlan(
            include=context.form.include_variables.data,
            section_key='variables',
            importer=lambda section: _import_variables(context.user_id, section),
            singular_label='variable',
            plural_label='variables',
        ),
        _SectionImportPlan(
            include=context.form.include_secrets.data,
            section_key='secrets',
            importer=lambda section: _import_secrets(
                context.user_id, section, context.secret_key
            ),
            singular_label='secret',
            plural_label='secrets',
        ),
        _SectionImportPlan(
            include=context.form.include_history.data,
            section_key='change_history',
            importer=lambda section: _import_change_history(
                context.user_id, section
            ),
            singular_label='history event',
            plural_label='history events',
        ),
    ]

    for plan in section_importers:
        _import_section(context, plan)


def _handle_import_source_files(context: _ImportContext) -> None:
    if not context.form.include_source.data:
        return

    selected_source_categories = list(_APP_SOURCE_CATEGORIES)
    app_source_section, app_source_errors, fatal = _load_export_section(
        context.data,
        'app_source',
        context.cid_lookup,
    )
    context.errors.extend(app_source_errors)

    if fatal:
        return

    _verify_import_source_files(
        app_source_section,
        selected_source_categories,
        context.warnings,
        context.info_messages,
    )


def _generate_snapshot_export(user_id: str) -> dict[str, Any] | None:
    """Generate a snapshot export equivalent to the default export.

    Returns:
        Export result dict with 'cid_value', 'download_path', 'json_payload', and 'generated_at',
        or None if generation fails.
    """
    try:
        form = ExportForm()
        # Set snapshot defaults: aliases, servers, variables enabled; secrets, history, source disabled
        form.snapshot.data = True
        form.include_aliases.data = True
        form.include_servers.data = True
        form.include_variables.data = True
        form.include_secrets.data = False
        form.include_history.data = False
        form.include_source.data = False
        form.include_cid_map.data = True
        form.include_unreferenced_cid_data.data = False

        # Initialize form selections by building preview (this populates selected_* fields)
        _build_export_preview(form, user_id)

        export_result = _build_export_payload(form, user_id, store_content=True)
        # Record the export
        record_export(user_id, export_result['cid_value'])

        # Add generated_at timestamp
        export_result['generated_at'] = datetime.now(timezone.utc).isoformat()
        return export_result
    except Exception as e:
        # If snapshot generation fails, log the error but don't fail the import
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate snapshot export after import: {e}", exc_info=True)
        return None


def _finalise_import(context: _ImportContext, render_form: Callable[[], Any]) -> Any:
    from flask import session

    for message in context.errors:
        flash(message, 'danger')

    for message in context.warnings:
        flash(message, 'warning')

    if context.summaries:
        summary_text = ', '.join(context.summaries)
        flash(f'Imported {summary_text}.', 'success')

    for message in context.info_messages:
        flash(message, 'success')

    # Generate and store snapshot export after import completes
    snapshot_export = _generate_snapshot_export(context.user_id)
    context.snapshot_export = snapshot_export

    # Store snapshot info in session for display on redirected page
    if snapshot_export:
        session['import_snapshot_export'] = {
            'cid': snapshot_export['cid_value'],
            'generated_at': snapshot_export['generated_at'],
        }

    if context.errors or context.warnings or context.summaries:
        record_entity_interaction(
            EntityInteractionRequest(
                user_id=context.user_id,
                entity_type='import',
                entity_name='json',
                action='save',
                message=context.change_message,
                content=context.raw_payload,
            )
        )

        return redirect(url_for('main.import_data'))

    return render_form(snapshot_export)


def _process_import_submission(
    form: ImportForm,
    change_message: str,
    render_form: Callable[[], Any],
) -> Any:
    """Handle an import form submission and return the appropriate response."""

    raw_payload = _load_import_payload(form)
    if raw_payload is None:
        return render_form()

    parsed_payload, error_message = _parse_import_payload(raw_payload)
    if error_message:
        flash(error_message, 'danger')
        return render_form()

    assert parsed_payload is not None  # For type checkers.
    context = _create_import_context(form, change_message, parsed_payload)
    _ingest_import_cid_map(context)
    _import_selected_sections(context)
    _handle_import_source_files(context)

    return _finalise_import(context, render_form)


def _verify_import_source_category(
    entries: Any,
    label_text: str,
    warnings: list[str],
    info_messages: list[str],
) -> None:
    lower_label = label_text.lower()

    if entries is None:
        warnings.append(f'No {lower_label} were included in the import data.')
        return

    if not isinstance(entries, list):
        warnings.append(f'{label_text} section must be a list of file entries.')
        return

    base_path = _app_root_path()
    base_resolved = base_path.resolve()
    checked_any = False
    mismatches_found = False

    for raw_entry in entries:
        parsed_entry = _parse_source_entry(raw_entry, label_text, warnings)
        if parsed_entry is None:
            mismatches_found = True
            continue

        absolute_path = _resolve_source_entry(parsed_entry, base_path, base_resolved, warnings)
        if absolute_path is None:
            mismatches_found = True
            continue

        checked_any = True
        content = _load_source_entry_bytes(absolute_path, parsed_entry, warnings)
        if content is None:
            mismatches_found = True
            continue

        if not _source_entry_matches_export(parsed_entry, content, warnings):
            mismatches_found = True

    if checked_any and not mismatches_found:
        info_messages.append(f'All {lower_label} match the export.')
    elif not checked_any:
        warnings.append(f'No valid {lower_label} were found in the import data.')


def _verify_import_source_files(
    raw_section: Any,
    selected_categories: list[tuple[str, str]],
    warnings: list[str],
    info_messages: list[str],
) -> None:
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
        _verify_import_source_category(entries, label_text, warnings, info_messages)


def _load_import_payload(form: ImportForm) -> str | None:
    """Return JSON content based on the selected import source."""
    source = form.import_source.data

    if source == 'file':
        file_storage = form.import_file.data
        if not file_storage:
            form.import_file.errors.append('Choose a JSON file to upload.')
            return None
        try:
            raw_bytes = file_storage.read()
        except Exception:
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

    return None


def _import_aliases(
    user_id: str,
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> Tuple[int, list[str]]:
    """Import alias definitions from JSON data."""
    if raw_aliases is None:
        return 0, ['No alias data found in import file.']
    if not isinstance(raw_aliases, list):
        return 0, ['Aliases in import file must be a list.']

    errors: list[str] = []
    imported = 0
    reserved_routes = get_existing_routes()
    cid_map = cid_map or {}

    for entry in raw_aliases:
        prepared = _prepare_alias_import(entry, reserved_routes, cid_map, errors)
        if prepared is None:
            continue

        existing = get_alias_by_name(user_id, prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            existing.template = prepared.template
            save_entity(existing)
        else:
            alias = Alias(
                name=prepared.name,
                user_id=user_id,
                definition=prepared.definition,
                enabled=prepared.enabled,
                template=prepared.template,
            )
            save_entity(alias)
        imported += 1

    return imported, errors


@dataclass
class _ServerImport:
    name: str
    definition: str
    enabled: bool
    template: bool


def _load_server_definition_from_cid(
    name: str,
    definition_cid: str,
    cid_map: dict[str, bytes],
    errors: list[str],
) -> str | None:
    cid_bytes = _load_cid_bytes(definition_cid, cid_map)
    if cid_bytes is None:
        errors.append(
            f'Server "{name}" definition with CID "{definition_cid}" was not included in the import.'
        )
        return None
    try:
        return cid_bytes.decode('utf-8')
    except UnicodeDecodeError:
        errors.append(
            f'Server "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
        )
        return None


def _prepare_server_import(
    entry: Any,
    cid_map: dict[str, bytes],
    errors: list[str],
) -> _ServerImport | None:
    if not isinstance(entry, dict):
        errors.append('Server entries must be objects with name and definition details.')
        return None

    name_raw = entry.get('name')
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append('Server entry must include a valid name.')
        return None

    name = name_raw.strip()
    definition_text: str | None = None
    raw_definition = entry.get('definition')
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Server "{name}" definition must be text.')
        return None

    definition_cid = _normalise_cid(entry.get('definition_cid'))
    if definition_text is None and definition_cid:
        definition_text = _load_server_definition_from_cid(name, definition_cid, cid_map, errors)

    if definition_text is None:
        errors.append(
            f'Server "{name}" entry must include either a definition or a definition_cid.'
        )
        return None

    enabled = _coerce_enabled_flag(entry.get('enabled'))
    template = _coerce_enabled_flag(entry.get('template'))

    return _ServerImport(
        name=name,
        definition=definition_text,
        enabled=enabled,
        template=template,
    )


def _import_servers(
    user_id: str,
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> Tuple[int, list[str]]:
    """Import server definitions from JSON data."""
    if raw_servers is None:
        return 0, ['No server data found in import file.']
    if not isinstance(raw_servers, list):
        return 0, ['Servers in import file must be a list.']

    errors: list[str] = []
    imported = 0
    cid_map = cid_map or {}

    for entry in raw_servers:
        prepared = _prepare_server_import(entry, cid_map, errors)
        if prepared is None:
            continue

        definition_cid = save_server_definition_as_cid(prepared.definition, user_id)
        existing = get_server_by_name(user_id, prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.definition_cid = definition_cid
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            existing.template = prepared.template
            save_entity(existing)
        else:
            server = Server(
                name=prepared.name,
                definition=prepared.definition,
                user_id=user_id,
                definition_cid=definition_cid,
                enabled=prepared.enabled,
                template=prepared.template,
            )
            save_entity(server)
        imported += 1

    if imported:
        update_server_definitions_cid(user_id)

    return imported, errors


def _import_variables(user_id: str, raw_variables: Any) -> Tuple[int, list[str]]:
    """Import variable definitions from JSON data."""
    if raw_variables is None:
        return 0, ['No variable data found in import file.']
    if not isinstance(raw_variables, list):
        return 0, ['Variables in import file must be a list.']

    errors: list[str] = []
    imported = 0

    for entry in raw_variables:
        if not isinstance(entry, dict):
            errors.append('Variable entries must be objects with name and definition.')
            continue

        name = entry.get('name')
        definition = entry.get('definition')
        if not name or definition is None:
            errors.append('Variable entry must include both name and definition.')
            continue

        enabled = _coerce_enabled_flag(entry.get('enabled'))
        template = _coerce_enabled_flag(entry.get('template'))

        existing = get_variable_by_name(user_id, name)
        if existing:
            existing.definition = definition
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = enabled
            existing.template = template
            save_entity(existing)
        else:
            variable = Variable(
                name=name,
                definition=definition,
                user_id=user_id,
                enabled=enabled,
                template=template,
            )
            save_entity(variable)
        imported += 1

    if imported:
        update_variable_definitions_cid(user_id)

    return imported, errors


def _normalise_secret_items(raw_secrets: Any) -> Iterable[dict[str, Any]] | None:
    if raw_secrets is None:
        return None
    if isinstance(raw_secrets, dict):
        items = raw_secrets.get('items')
    else:
        items = raw_secrets
    if not isinstance(items, list):
        return None
    return items


def _import_secrets(user_id: str, raw_secrets: Any, key: str) -> Tuple[int, list[str]]:
    """Import secret definitions from JSON data."""
    items = _normalise_secret_items(raw_secrets)
    if items is None:
        return 0, ['No secret data found in import file.']

    errors: list[str] = []
    imported = 0

    try:
        for entry in items:
            if not isinstance(entry, dict):
                errors.append('Secret entries must be objects with name and encrypted value.')
                continue

            name = entry.get('name')
            ciphertext = entry.get('ciphertext') or entry.get('definition')
            if not name or not ciphertext:
                errors.append('Secret entries must include name and encrypted value.')
                continue

            plaintext = decrypt_secret_value(ciphertext, key)
            enabled = _coerce_enabled_flag(entry.get('enabled'))
            template = _coerce_enabled_flag(entry.get('template'))
            existing = get_secret_by_name(user_id, name)
            if existing:
                existing.definition = plaintext
                existing.updated_at = datetime.now(timezone.utc)
                existing.enabled = enabled
                existing.template = template
                save_entity(existing)
            else:
                secret = Secret(
                    name=name,
                    definition=plaintext,
                    user_id=user_id,
                    enabled=enabled,
                    template=template,
                )
                save_entity(secret)
            imported += 1
    except ValueError:
        return 0, ['Invalid decryption key for secrets.']

    if imported:
        update_secret_definitions_cid(user_id)

    return imported, errors


def _serialise_interaction_history(user_id: str, entity_type: str, entity_name: str) -> list[dict[str, str]]:
    interactions = get_entity_interactions(user_id, entity_type, entity_name)

    history: list[dict[str, str]] = []
    for interaction in interactions:
        timestamp = interaction.created_at
        if timestamp is None:
            continue
        aware = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        aware = aware.astimezone(timezone.utc)
        history.append(
            {
                'timestamp': aware.isoformat(),
                'message': (interaction.message or '').strip(),
                'action': (interaction.action or '').strip() or 'save',
            }
        )

    return history


def _gather_change_history(user_id: str) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Return change history grouped by entity collection."""

    collections: dict[str, tuple[str, Iterable[str]]] = {
        'aliases': ('alias', (alias.name for alias in get_user_aliases(user_id))),
        'servers': ('server', (server.name for server in get_user_servers(user_id))),
        'variables': ('variable', (variable.name for variable in get_user_variables(user_id))),
        'secrets': ('secret', (secret.name for secret in get_user_secrets(user_id))),
    }

    history_payload: dict[str, dict[str, list[dict[str, str]]]] = {}

    for key, (entity_type, names) in collections.items():
        collection_history: dict[str, list[dict[str, str]]] = {}
        for name in names:
            events = _serialise_interaction_history(user_id, entity_type, name)
            if events:
                collection_history[name] = events
        if collection_history:
            history_payload[key] = collection_history

    return history_payload


def _parse_history_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith('Z'):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass
class _HistoryEvent:
    timestamp: datetime
    action: str
    message: str
    content: str


def _normalise_history_name(
    collection_key: str,
    raw_name: Any,
    errors: list[str],
) -> str | None:
    if not isinstance(raw_name, str) or not raw_name.strip():
        errors.append(f'{collection_key.title()} history entry must include a valid item name.')
        return None
    return raw_name.strip()


def _prepare_history_event(
    name: str,
    raw_event: Any,
    errors: list[str],
) -> _HistoryEvent | None:
    if not isinstance(raw_event, dict):
        errors.append(f'History events for "{name}" must be objects.')
        return None

    timestamp_raw = raw_event.get('timestamp')
    timestamp = _parse_history_timestamp(timestamp_raw or '')
    if timestamp is None:
        errors.append(f'History event for "{name}" has an invalid timestamp.')
        return None

    action_raw = raw_event.get('action')
    action = (action_raw if isinstance(action_raw, str) else '').strip() or 'save'
    message_raw = raw_event.get('message')
    message = (message_raw if isinstance(message_raw, str) else '').strip()
    if len(message) > 500:
        message = message[:497] + '…'
    content_raw = raw_event.get('content')
    content = (content_raw if isinstance(content_raw, str) else '').strip()

    return _HistoryEvent(
        timestamp=timestamp,
        action=action,
        message=message,
        content=content,
    )


def _iter_history_events(
    raw_history: dict[str, Any],
    collection_key: str,
    errors: list[str],
) -> Iterator[tuple[str, _HistoryEvent]]:
    entries = raw_history.get(collection_key)
    if entries is None:
        return
    if not isinstance(entries, dict):
        errors.append(f'{collection_key.title()} history must map item names to event lists.')
        return

    for raw_name, raw_events in entries.items():
        name = _normalise_history_name(collection_key, raw_name, errors)
        if not name:
            continue
        if not isinstance(raw_events, list):
            errors.append(f'History for "{raw_name}" must be a list of events.')
            continue
        for raw_event in raw_events:
            event = _prepare_history_event(name, raw_event, errors)
            if event is not None:
                yield name, event


def _import_change_history(user_id: str, raw_history: Any) -> Tuple[int, list[str]]:
    """Import change history events."""

    if raw_history is None:
        return 0, ['No change history data found in import file.']
    if not isinstance(raw_history, dict):
        return 0, ['Change history in import file must be an object mapping collections to events.']

    collection_map = {
        'aliases': 'alias',
        'servers': 'server',
        'variables': 'variable',
        'secrets': 'secret',
    }

    errors: list[str] = []
    imported = 0

    for key, entity_type in collection_map.items():
        for name, event in _iter_history_events(raw_history, key, errors):
            existing = find_entity_interaction(
                EntityInteractionLookup(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_name=name,
                    action=event.action,
                    message=event.message,
                    created_at=event.timestamp,
                )
            )
            if existing:
                continue

            record_entity_interaction(
                EntityInteractionRequest(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_name=name,
                    action=event.action,
                    message=event.message,
                    content=event.content,
                    created_at=event.timestamp,
                )
            )
            imported += 1

    return imported, errors


@main_bp.route('/export', methods=['GET', 'POST'])
def export_data():
    """Allow users to export selected data collections as JSON."""
    form = ExportForm()
    preview = _build_export_preview(form, current_user.id)
    recent_exports = get_user_exports(current_user.id, limit=100)
    if form.validate_on_submit():
        export_result = _build_export_payload(form, current_user.id)
        # Record the export
        record_export(current_user.id, export_result['cid_value'])
        return render_template('export_result.html', **export_result)

    return render_template('export.html', form=form, export_preview=preview, recent_exports=recent_exports)


@main_bp.route('/export/size', methods=['POST'])
def export_size():
    """Return the size of the export JSON for the current selections."""

    form = ExportForm()
    _build_export_preview(form, current_user.id)
    if form.validate():
        export_result = _build_export_payload(
            form,
            current_user.id,
            store_content=False,
        )
        json_bytes = export_result['json_payload'].encode('utf-8')
        size_bytes = len(json_bytes)
        return {
            'ok': True,
            'size_bytes': size_bytes,
            'formatted_size': _format_size(size_bytes),
        }

    return {'ok': False, 'errors': form.errors}, 400


@main_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """Allow users to import data collections from JSON content."""
    from flask import jsonify, session

    # Check if this is a JSON request (REST API)
    # Flask's test client sets request.is_json when using json= parameter
    is_json_request = request.is_json or (request.method == 'POST' and request.content_type and 'application/json' in request.content_type.lower())

    if is_json_request and request.method == 'POST':
        # Handle JSON API request
        try:
            json_data = request.get_json() or {}
            # Create a mock form-like structure for JSON requests
            # For now, we'll use the existing import mechanism
            # Convert JSON payload to raw text
            raw_payload = json.dumps(json_data) if isinstance(json_data, dict) else json_data

            # Parse the payload
            parsed_payload, error_message = _parse_import_payload(raw_payload)
            if error_message:
                return jsonify({'ok': False, 'error': error_message}), 400

            assert parsed_payload is not None  # For type checkers

            # Create import context with default form settings
            form = ImportForm()
            form.include_aliases.data = 'aliases' in parsed_payload.data
            form.include_servers.data = 'servers' in parsed_payload.data
            form.include_variables.data = 'variables' in parsed_payload.data
            form.include_secrets.data = 'secrets' in parsed_payload.data
            form.include_history.data = 'change_history' in parsed_payload.data
            form.process_cid_map.data = 'cid_values' in parsed_payload.data
            form.include_source.data = False

            context = _create_import_context(form, 'REST API import', parsed_payload)
            _ingest_import_cid_map(context)
            _import_selected_sections(context)
            _handle_import_source_files(context)

            # Generate snapshot export
            snapshot_export = _generate_snapshot_export(context.user_id)

            # Return JSON response
            response_data = {'ok': True}
            if context.errors:
                response_data['errors'] = context.errors
            if context.warnings:
                response_data['warnings'] = context.warnings
            if context.summaries:
                response_data['summaries'] = context.summaries
            if snapshot_export:
                response_data['snapshot'] = {
                    'cid': snapshot_export['cid_value'],
                    'generated_at': snapshot_export['generated_at'],
                }

            return jsonify(response_data), 200
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 400

    # Handle HTML form request
    form = ImportForm()
    change_message = (request.form.get('change_message') or '').strip()

    def _render_import_form(snapshot_export: dict[str, Any] | None = None):
        interactions = load_interaction_history(current_user.id, 'import', 'json')
        # Get snapshot info from session if available
        snapshot_info = session.pop('import_snapshot_export', None) or snapshot_export
        return render_template('import.html', form=form, import_interactions=interactions, snapshot_export=snapshot_info)

    if form.validate_on_submit():
        return _process_import_submission(form, change_message, _render_import_form)

    return _render_import_form()


__all__ = ['export_data', 'export_size', 'import_data']
