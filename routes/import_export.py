"""Routes for exporting and importing user configuration data."""
from __future__ import annotations

import json
import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Tuple

import requests
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from auth_providers import require_login
from alias_matching import PatternError, normalise_pattern
from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid, save_server_definition_as_cid, store_cid_from_bytes, store_cid_from_json
from db_access import (
    get_alias_by_name,
    get_cid_by_path,
    get_secret_by_name,
    get_server_by_name,
    get_user_aliases,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    get_variable_by_name,
    record_entity_interaction,
    save_entity,
)
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from forms import ExportForm, ImportForm
from models import Alias, EntityInteraction, Secret, Server, Variable

from . import main_bp
from .core import get_existing_routes
from .secrets import update_secret_definitions_cid
from .servers import update_server_definitions_cid
from .variables import update_variable_definitions_cid
from interaction_log import load_interaction_history


def _normalise_cid(value: Any) -> str:
    if not isinstance(value, str):
        return ''
    cleaned = value.strip()
    if not cleaned:
        return ''
    cleaned = cleaned.split('.')[0]
    return cleaned.lstrip('/')


def _serialise_cid_value(content: bytes) -> dict[str, str]:
    try:
        return {'encoding': 'utf-8', 'value': content.decode('utf-8')}
    except UnicodeDecodeError:
        return {'encoding': 'base64', 'value': base64.b64encode(content).decode('ascii')}


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

_PYTHON_SOURCE_EXCLUDED_DIRS: set[str] = {'test', 'tests', '__pycache__'}
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

    for entry in entries:
        if not isinstance(entry, dict):
            warnings.append(f'{label_text} entry must include "path" and "cid" fields.')
            mismatches_found = True
            continue

        raw_path = entry.get('path')
        expected_cid = _normalise_cid(entry.get('cid'))
        if not isinstance(raw_path, str) or not expected_cid:
            warnings.append(f'{label_text} entry must include valid "path" and "cid" values.')
            mismatches_found = True
            continue

        candidate_path = Path(raw_path)
        if candidate_path.is_absolute() or '..' in candidate_path.parts:
            warnings.append(f'Source file "{raw_path}" used an invalid path.')
            mismatches_found = True
            continue

        absolute_path = (base_path / candidate_path).resolve()
        try:
            absolute_path.relative_to(base_resolved)
        except ValueError:
            warnings.append(f'Source file "{raw_path}" used an invalid path.')
            mismatches_found = True
            continue

        if not absolute_path.exists():
            warnings.append(f'Source file "{raw_path}" is missing locally.')
            mismatches_found = True
            continue

        if not absolute_path.is_file():
            warnings.append(f'Source path "{raw_path}" is not a file locally.')
            mismatches_found = True
            continue

        checked_any = True
        try:
            local_bytes = absolute_path.read_bytes()
        except OSError:
            warnings.append(f'Source file "{raw_path}" could not be read locally.')
            mismatches_found = True
            continue

        local_cid = format_cid(generate_cid(local_bytes))
        if _normalise_cid(expected_cid) != local_cid:
            warnings.append(f'Source file "{raw_path}" differs from the export.')
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


def _import_aliases(user_id: str, raw_aliases: Any) -> Tuple[int, list[str]]:
    """Import alias definitions from JSON data."""
    if raw_aliases is None:
        return 0, ['No alias data found in import file.']
    if not isinstance(raw_aliases, list):
        return 0, ['Aliases in import file must be a list.']

    errors: list[str] = []
    imported = 0
    reserved_routes = get_existing_routes()

    for entry in raw_aliases:
        if not isinstance(entry, dict):
            errors.append('Alias entries must be objects with name and target_path.')
            continue

        name = entry.get('name')
        target_path = entry.get('target_path')
        if not name or not target_path:
            errors.append('Alias entry must include both name and target_path.')
            continue

        if f'/{name}' in reserved_routes:
            errors.append(f'Alias "{name}" conflicts with an existing route and was skipped.')
            continue

        match_type = (entry.get('match_type') or 'literal').lower()
        match_pattern = entry.get('match_pattern')
        ignore_case = bool(entry.get('ignore_case', False))

        try:
            normalised_pattern = normalise_pattern(match_type, match_pattern, name)
        except PatternError as exc:
            errors.append(f'Alias "{name}" skipped: {exc}')
            continue

        existing = get_alias_by_name(user_id, name)
        if existing:
            existing.target_path = target_path
            existing.match_type = match_type
            existing.match_pattern = normalised_pattern
            existing.ignore_case = ignore_case
            existing.updated_at = datetime.now(timezone.utc)
            save_entity(existing)
        else:
            alias = Alias(
                name=name,
                target_path=target_path,
                user_id=user_id,
                match_type=match_type,
                match_pattern=normalised_pattern,
                ignore_case=ignore_case,
            )
            save_entity(alias)
        imported += 1

    return imported, errors


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
        if not isinstance(entry, dict):
            errors.append('Server entries must be objects with name and definition details.')
            continue

        name_raw = entry.get('name')
        if not isinstance(name_raw, str) or not name_raw.strip():
            errors.append('Server entry must include a valid name.')
            continue

        name = name_raw.strip()

        definition_text: str | None = None
        raw_definition = entry.get('definition')
        if isinstance(raw_definition, str):
            definition_text = raw_definition
        elif raw_definition is not None:
            errors.append(f'Server "{name}" definition must be text.')
            continue

        definition_cid = _normalise_cid(entry.get('definition_cid'))

        if definition_text is None and definition_cid:
            cid_bytes = _load_cid_bytes(definition_cid, cid_map)
            if cid_bytes is None:
                errors.append(
                    f'Server "{name}" definition with CID "{definition_cid}" was not included in the import.'
                )
                continue
            try:
                definition_text = cid_bytes.decode('utf-8')
            except UnicodeDecodeError:
                errors.append(
                    f'Server "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
                )
                continue

        if definition_text is None:
            errors.append(
                f'Server "{name}" entry must include either a definition or a definition_cid.'
            )
            continue

        definition_cid = save_server_definition_as_cid(definition_text, user_id)
        existing = get_server_by_name(user_id, name)
        if existing:
            existing.definition = definition_text
            existing.definition_cid = definition_cid
            existing.updated_at = datetime.now(timezone.utc)
            save_entity(existing)
        else:
            server = Server(
                name=name,
                definition=definition_text,
                user_id=user_id,
                definition_cid=definition_cid,
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

        existing = get_variable_by_name(user_id, name)
        if existing:
            existing.definition = definition
            existing.updated_at = datetime.now(timezone.utc)
            save_entity(existing)
        else:
            variable = Variable(name=name, definition=definition, user_id=user_id)
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
            existing = get_secret_by_name(user_id, name)
            if existing:
                existing.definition = plaintext
                existing.updated_at = datetime.now(timezone.utc)
                save_entity(existing)
            else:
                secret = Secret(name=name, definition=plaintext, user_id=user_id)
                save_entity(secret)
            imported += 1
    except ValueError:
        return 0, ['Invalid decryption key for secrets.']

    if imported:
        update_secret_definitions_cid(user_id)

    return imported, errors


def _serialise_interaction_history(user_id: str, entity_type: str, entity_name: str) -> list[dict[str, str]]:
    interactions = (
        EntityInteraction.query
        .filter_by(user_id=user_id, entity_type=entity_type, entity_name=entity_name)
        .order_by(EntityInteraction.created_at.asc(), EntityInteraction.id.asc())
        .all()
    )

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
        entries = raw_history.get(key)
        if entries is None:
            continue
        if not isinstance(entries, dict):
            errors.append(f'{key.title()} history must map item names to event lists.')
            continue

        for raw_name, raw_events in entries.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                errors.append(f'{key.title()} history entry must include a valid item name.')
                continue
            if not isinstance(raw_events, list):
                errors.append(f'History for "{raw_name}" must be a list of events.')
                continue

            name = raw_name.strip()
            for raw_event in raw_events:
                if not isinstance(raw_event, dict):
                    errors.append(f'History events for "{name}" must be objects.')
                    continue

                timestamp_raw = raw_event.get('timestamp')
                timestamp = _parse_history_timestamp(timestamp_raw or '')
                if timestamp is None:
                    errors.append(f'History event for "{name}" has an invalid timestamp.')
                    continue

                action_raw = raw_event.get('action')
                action = (action_raw if isinstance(action_raw, str) else '').strip() or 'save'
                message_raw = raw_event.get('message')
                message = (message_raw if isinstance(message_raw, str) else '').strip()
                if len(message) > 500:
                    message = message[:497] + '…'
                content_raw = raw_event.get('content')
                content = (content_raw if isinstance(content_raw, str) else '').strip()

                existing = (
                    EntityInteraction.query
                    .filter_by(
                        user_id=user_id,
                        entity_type=entity_type,
                        entity_name=name,
                        action=action,
                        message=message,
                    )
                    .filter(EntityInteraction.created_at == timestamp)
                    .first()
                )
                if existing:
                    continue

                record_entity_interaction(
                    user_id,
                    entity_type,
                    name,
                    action,
                    message,
                    content,
                    created_at=timestamp,
                )
                imported += 1

    return imported, errors


@main_bp.route('/export', methods=['GET', 'POST'])
@require_login
def export_data():
    """Allow users to export selected data collections as JSON."""
    form = ExportForm()
    if form.validate_on_submit():
        payload: dict[str, Any] = {
            'version': 4,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

        cid_map_entries: dict[str, dict[str, str]] = {}
        base_path = _app_root_path()

        def _record_cid_value(cid_value: str, content: bytes) -> None:
            if not form.include_cid_map.data:
                return
            normalised = _normalise_cid(cid_value)
            if not normalised or normalised in cid_map_entries:
                return
            cid_map_entries[normalised] = _serialise_cid_value(content)

        if form.include_aliases.data:
            payload['aliases'] = [
                {
                    'name': alias.name,
                    'target_path': alias.target_path,
                    'match_type': alias.match_type,
                    'match_pattern': alias.get_effective_pattern(),
                    'ignore_case': bool(alias.ignore_case),
                }
                for alias in get_user_aliases(current_user.id)
            ]

        if form.include_servers.data:
            servers_payload: list[dict[str, str]] = []
            for server in get_user_servers(current_user.id):
                definition_text = server.definition or ''
                definition_bytes = definition_text.encode('utf-8')
                definition_cid = server.definition_cid or save_server_definition_as_cid(
                    definition_text,
                    current_user.id,
                )
                servers_payload.append(
                    {
                        'name': server.name,
                        'definition_cid': definition_cid,
                    }
                )
                _record_cid_value(definition_cid, definition_bytes)
            if servers_payload:
                payload['servers'] = servers_payload

        if form.include_variables.data:
            payload['variables'] = [
                {
                    'name': variable.name,
                    'definition': variable.definition,
                }
                for variable in get_user_variables(current_user.id)
            ]

        if form.include_secrets.data:
            key = form.secret_key.data.strip()
            payload['secrets'] = {
                'encryption': SECRET_ENCRYPTION_SCHEME,
                'items': [
                    {
                        'name': secret.name,
                        'ciphertext': encrypt_secret_value(secret.definition, key),
                    }
                    for secret in get_user_secrets(current_user.id)
                ],
            }

        if form.include_history.data:
            history_payload = _gather_change_history(current_user.id)
            if history_payload:
                payload['change_history'] = history_payload

        app_source_payload: dict[str, list[dict[str, str]]] = {}
        if form.include_source.data:
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

                    cid_value = store_cid_from_bytes(content_bytes, current_user.id)
                    _record_cid_value(cid_value, content_bytes)
                    entries.append({
                        'path': relative_path.as_posix(),
                        'cid': cid_value,
                    })

                if entries:
                    app_source_payload[category] = entries

        if app_source_payload:
            payload['app_source'] = app_source_payload

        if form.include_cid_map.data and cid_map_entries:
            payload['cid_values'] = {cid: cid_map_entries[cid] for cid in sorted(cid_map_entries)}

        json_payload = json.dumps(payload, indent=2, sort_keys=True)
        cid_value = store_cid_from_json(json_payload, current_user.id)
        download_path = cid_path(cid_value, 'json') or ''
        return render_template(
            'export_result.html',
            cid_value=cid_value,
            download_path=download_path,
            json_payload=json_payload,
        )

    return render_template('export.html', form=form)


@main_bp.route('/import', methods=['GET', 'POST'])
@require_login
def import_data():
    """Allow users to import data collections from JSON content."""
    form = ImportForm()
    change_message = (request.form.get('change_message') or '').strip()

    def _render_import_form():
        interactions = load_interaction_history(current_user.id, 'import', 'json')
        return render_template('import.html', form=form, import_interactions=interactions)

    if form.validate_on_submit():
        raw_payload = _load_import_payload(form)
        if raw_payload is None:
            return _render_import_form()

        raw_payload = raw_payload.strip()
        if not raw_payload:
            flash('Import data was empty.', 'danger')
            return _render_import_form()

        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            flash(f'Failed to parse JSON: {exc}', 'danger')
            return _render_import_form()

        if not isinstance(data, dict):
            flash('Import file must contain a JSON object.', 'danger')
            return _render_import_form()

        user_id = current_user.id
        errors: list[str] = []
        warnings: list[str] = []
        info_messages: list[str] = []
        summaries: list[str] = []
        cid_lookup: dict[str, bytes] = {}

        if form.process_cid_map.data:
            parsed_cids, cid_map_errors = _parse_cid_values_section(data.get('cid_values'))
            errors.extend(cid_map_errors)

            for cid_value, content_bytes in parsed_cids.items():
                expected_cid = _normalise_cid(format_cid(generate_cid(content_bytes)))
                if expected_cid and cid_value != expected_cid:
                    errors.append(
                        f'CID "{cid_value}" content did not match its hash and was skipped.'
                    )
                    continue
                store_cid_from_bytes(content_bytes, user_id)
                cid_lookup[cid_value] = content_bytes

        imported_aliases = 0
        alias_errors: list[str] = []
        if form.include_aliases.data:
            imported_aliases, alias_errors = _import_aliases(user_id, data.get('aliases'))
            errors.extend(alias_errors)
            if imported_aliases:
                label = 'aliases' if imported_aliases != 1 else 'alias'
                summaries.append(f'{imported_aliases} {label}')

        imported_servers = 0
        server_errors: list[str] = []
        if form.include_servers.data:
            imported_servers, server_errors = _import_servers(
                user_id,
                data.get('servers'),
                cid_lookup,
            )
            errors.extend(server_errors)
            if imported_servers:
                label = 'servers' if imported_servers != 1 else 'server'
                summaries.append(f'{imported_servers} {label}')

        imported_variables = 0
        variable_errors: list[str] = []
        if form.include_variables.data:
            imported_variables, variable_errors = _import_variables(user_id, data.get('variables'))
            errors.extend(variable_errors)
            if imported_variables:
                label = 'variables' if imported_variables != 1 else 'variable'
                summaries.append(f'{imported_variables} {label}')

        imported_secrets = 0
        secret_errors: list[str] = []
        if form.include_secrets.data:
            imported_secrets, secret_errors = _import_secrets(
                user_id,
                data.get('secrets'),
                form.secret_key.data.strip(),
            )
            errors.extend(secret_errors)
            if imported_secrets:
                label = 'secrets' if imported_secrets != 1 else 'secret'
                summaries.append(f'{imported_secrets} {label}')

        imported_history = 0
        history_errors: list[str] = []
        if form.include_history.data:
            imported_history, history_errors = _import_change_history(user_id, data.get('change_history'))
            errors.extend(history_errors)
            if imported_history:
                label = 'history events' if imported_history != 1 else 'history event'
                summaries.append(f'{imported_history} {label}')

        selected_source_categories: list[tuple[str, str]] = []
        if form.include_source.data:
            selected_source_categories = list(_APP_SOURCE_CATEGORIES)

        if selected_source_categories:
            _verify_import_source_files(
                data.get('app_source'),
                selected_source_categories,
                warnings,
                info_messages,
            )

        for message in errors:
            flash(message, 'danger')

        for message in warnings:
            flash(message, 'warning')

        if summaries:
            summary_text = ', '.join(summaries)
            flash(f'Imported {summary_text}.', 'success')

        for message in info_messages:
            flash(message, 'success')

        if errors or warnings or summaries:
            record_entity_interaction(
                user_id,
                'import',
                'json',
                'save',
                change_message,
                raw_payload,
            )

        if errors or warnings or summaries:
            return redirect(url_for('main.import_data'))

    return _render_import_form()


__all__ = ['export_data', 'import_data']
