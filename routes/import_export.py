"""Routes for exporting and importing user configuration data."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Tuple

import requests
from flask import current_app, flash, redirect, render_template, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_utils import save_server_definition_as_cid
from db_access import (
    get_alias_by_name,
    get_secret_by_name,
    get_server_by_name,
    get_user_aliases,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    get_variable_by_name,
    save_entity,
)
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from forms import ExportForm, ImportForm
from models import Alias, Secret, Server, Variable

from . import main_bp
from .core import get_existing_routes
from .secrets import update_secret_definitions_cid
from .servers import update_server_definitions_cid
from .variables import update_variable_definitions_cid


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

        existing = get_alias_by_name(user_id, name)
        if existing:
            existing.target_path = target_path
            existing.updated_at = datetime.now(timezone.utc)
            save_entity(existing)
        else:
            alias = Alias(name=name, target_path=target_path, user_id=user_id)
            save_entity(alias)
        imported += 1

    return imported, errors


def _import_servers(user_id: str, raw_servers: Any) -> Tuple[int, list[str]]:
    """Import server definitions from JSON data."""
    if raw_servers is None:
        return 0, ['No server data found in import file.']
    if not isinstance(raw_servers, list):
        return 0, ['Servers in import file must be a list.']

    errors: list[str] = []
    imported = 0

    for entry in raw_servers:
        if not isinstance(entry, dict):
            errors.append('Server entries must be objects with name and definition.')
            continue

        name = entry.get('name')
        definition = entry.get('definition')
        if not name or definition is None:
            errors.append('Server entry must include both name and definition.')
            continue

        definition_cid = save_server_definition_as_cid(definition, user_id)
        existing = get_server_by_name(user_id, name)
        if existing:
            existing.definition = definition
            existing.definition_cid = definition_cid
            existing.updated_at = datetime.now(timezone.utc)
            save_entity(existing)
        else:
            server = Server(
                name=name,
                definition=definition,
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


@main_bp.route('/export', methods=['GET', 'POST'])
@require_login
def export_data():
    """Allow users to export selected data collections as JSON."""
    form = ExportForm()
    if form.validate_on_submit():
        payload: dict[str, Any] = {
            'version': 1,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

        if form.include_aliases.data:
            payload['aliases'] = [
                {
                    'name': alias.name,
                    'target_path': alias.target_path,
                }
                for alias in get_user_aliases(current_user.id)
            ]

        if form.include_servers.data:
            payload['servers'] = [
                {
                    'name': server.name,
                    'definition': server.definition,
                }
                for server in get_user_servers(current_user.id)
            ]

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

        json_payload = json.dumps(payload, indent=2, sort_keys=True)
        response = current_app.response_class(json_payload, mimetype='application/json')
        response.headers['Content-Disposition'] = 'attachment; filename=secureapp-export.json'
        return response

    return render_template('export.html', form=form)


@main_bp.route('/import', methods=['GET', 'POST'])
@require_login
def import_data():
    """Allow users to import data collections from JSON content."""
    form = ImportForm()
    if form.validate_on_submit():
        raw_payload = _load_import_payload(form)
        if raw_payload is None:
            return render_template('import.html', form=form)

        raw_payload = raw_payload.strip()
        if not raw_payload:
            flash('Import data was empty.', 'danger')
            return render_template('import.html', form=form)

        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            flash(f'Failed to parse JSON: {exc}', 'danger')
            return render_template('import.html', form=form)

        if not isinstance(data, dict):
            flash('Import file must contain a JSON object.', 'danger')
            return render_template('import.html', form=form)

        user_id = current_user.id
        errors: list[str] = []
        summaries: list[str] = []

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
            imported_servers, server_errors = _import_servers(user_id, data.get('servers'))
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

        for message in errors:
            flash(message, 'danger')

        if summaries:
            summary_text = ', '.join(summaries)
            flash(f'Imported {summary_text}.', 'success')

        if errors or summaries:
            return redirect(url_for('main.import_data'))

    return render_template('import.html', form=form)


__all__ = ['export_data', 'import_data']
