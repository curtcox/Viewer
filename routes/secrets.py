"""Secret management routes and helpers."""
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for

from cid_utils import (
    get_current_secret_definitions_cid,
    store_secret_definitions_cid,
)
from db_access import delete_entity, get_secret_by_name, get_user_secrets, save_entity
from forms import BulkSecretsForm, SecretForm
from identity import current_user
from interaction_log import load_interaction_history
from models import Secret
from serialization import model_to_dict

from . import main_bp
from .entities import create_entity, update_entity


_SECRET_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def update_secret_definitions_cid(user_id):
    """Update the secret definitions CID after secret changes."""
    return store_secret_definitions_cid(user_id)


def user_secrets():
    return get_user_secrets(current_user.id)


def _build_secrets_editor_payload(secrets: List[Secret]) -> str:
    """Return a JSON string representing the user's secrets for the editor."""

    return json.dumps(
        {secret.name: secret.definition for secret in secrets},
        indent=4,
        sort_keys=True,
        ensure_ascii=False,
    )


def _parse_secrets_editor_payload(raw_payload: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """Validate and normalize the JSON payload supplied by the bulk editor."""

    try:
        loaded = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc.msg}"

    if not isinstance(loaded, dict):
        return None, "Secrets JSON must be an object mapping secret names to values."

    normalized: Dict[str, str] = {}
    for name, value in loaded.items():
        if not isinstance(name, str):
            return None, "All secret names must be strings."
        if not _SECRET_NAME_PATTERN.fullmatch(name):
            return None, (
                f'Invalid secret name "{name}". Secret names may only contain '
                "letters, numbers, dots, hyphens, and underscores."
            )

        if isinstance(value, str):
            normalized[name] = value
        else:
            normalized[name] = json.dumps(value, ensure_ascii=False)

    return normalized, None


def _apply_secrets_editor_changes(user_id: str, desired_values: Dict[str, str], existing: List[Secret]) -> None:
    """Persist the desired secrets, replacing the user's current collection."""

    existing_by_name = {secret.name: secret for secret in existing}
    desired_names = set(desired_values.keys())

    for name in sorted(set(existing_by_name.keys()) - desired_names):
        delete_entity(existing_by_name[name])

    for name, definition in desired_values.items():
        current = existing_by_name.get(name)
        if current is None:
            save_entity(
                Secret(
                    name=name,
                    definition=definition,
                    user_id=user_id,
                )
            )
            continue

        if current.definition != definition:
            current.definition = definition
            current.updated_at = datetime.now(timezone.utc)
            save_entity(current)


@main_bp.route('/secrets')
def secrets():
    """Display user's secrets."""
    secrets_list = user_secrets()
    secret_definitions_cid = None
    if secrets_list:
        secret_definitions_cid = get_current_secret_definitions_cid(current_user.id)
    if _wants_structured_response():
        return jsonify([_secret_to_json(secret) for secret in secrets_list])
    return render_template(
        'secrets.html',
        secrets=secrets_list,
        secret_definitions_cid=secret_definitions_cid,
    )


@main_bp.route('/secrets/_/edit', methods=['GET', 'POST'])
def bulk_edit_secrets():
    """Edit all secrets at once using a JSON payload."""

    secrets_list = user_secrets()
    form = BulkSecretsForm()

    if request.method == 'GET':
        form.secrets_json.data = _build_secrets_editor_payload(secrets_list)

    if form.validate_on_submit():
        payload = form.secrets_json.data or ''
        normalized, error = _parse_secrets_editor_payload(payload)
        if error:
            form.secrets_json.errors.append(error)
        else:
            _apply_secrets_editor_changes(current_user.id, normalized, secrets_list)
            update_secret_definitions_cid(current_user.id)
            flash('Secrets updated successfully!', 'success')
            return redirect(url_for('main.secrets'))

    error_message = None
    if form.secrets_json.errors:
        error_message = form.secrets_json.errors[0]

    return render_template(
        'secrets_bulk_edit.html',
        form=form,
        error_message=error_message,
    )


@main_bp.route('/secrets/new', methods=['GET', 'POST'])
def new_secret():
    """Create a new secret."""
    form = SecretForm()

    change_message = (request.form.get('change_message') or '').strip()
    definition_text = form.definition.data or ''

    if form.validate_on_submit():
        if create_entity(
            Secret,
            form,
            current_user.id,
            'secret',
            change_message=change_message,
            content_text=definition_text,
        ):
            return redirect(url_for('main.secrets'))

    entity_name_hint = (form.name.data or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'secret', entity_name_hint)

    return render_template(
        'secret_form.html',
        form=form,
        title='Create New Secret',
        secret=None,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
    )


@main_bp.route('/secrets/<secret_name>')
def view_secret(secret_name):
    """View a specific secret."""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    if _wants_structured_response():
        return jsonify(_secret_to_json(secret))

    return render_template('secret_view.html', secret=secret)


@main_bp.route('/secrets/<secret_name>/edit', methods=['GET', 'POST'])
def edit_secret(secret_name):
    """Edit a specific secret."""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    form = SecretForm(obj=secret)

    change_message = (request.form.get('change_message') or '').strip()
    definition_text = form.definition.data or secret.definition or ''

    interaction_history = load_interaction_history(current_user.id, 'secret', secret.name)

    if form.validate_on_submit():
        if update_entity(
            secret,
            form,
            'secret',
            change_message=change_message,
            content_text=definition_text,
        ):
            return redirect(url_for('main.view_secret', secret_name=secret.name))
        return render_template(
            'secret_form.html',
            form=form,
            title=f'Edit Secret "{secret.name}"',
            secret=secret,
            interaction_history=interaction_history,
            ai_entity_name=secret.name,
            ai_entity_name_field=form.name.id,
        )

    return render_template(
        'secret_form.html',
        form=form,
        title=f'Edit Secret "{secret.name}"',
        secret=secret,
        interaction_history=interaction_history,
        ai_entity_name=secret.name,
        ai_entity_name_field=form.name.id,
    )


@main_bp.route('/secrets/<secret_name>/delete', methods=['POST'])
def delete_secret(secret_name):
    """Delete a specific secret."""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    delete_entity(secret)
    update_secret_definitions_cid(current_user.id)

    flash(f'Secret "{secret_name}" deleted successfully!', 'success')
    return redirect(url_for('main.secrets'))


__all__ = [
    'bulk_edit_secrets',
    'delete_secret',
    'edit_secret',
    'new_secret',
    'secrets',
    'update_secret_definitions_cid',
    'user_secrets',
    'view_secret',
]


def _wants_structured_response() -> bool:
    return getattr(g, "response_format", None) in {"json", "xml", "csv"}


def _secret_to_json(secret: Secret) -> Dict[str, object]:
    return model_to_dict(secret)

