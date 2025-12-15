"""Secret management routes and helpers."""
from typing import Dict, List, Optional, Tuple

from flask import abort, flash, redirect, render_template, request, url_for

from bulk_editor import create_secret_bulk_handler
from cid_utils import (
    get_current_secret_definitions_cid,
    store_secret_definitions_cid,
)
from db_access import (
    get_secret_by_name,
    get_secrets,
    get_template_secrets,
)
from forms import BulkSecretsForm, SecretForm
from interaction_log import load_interaction_history
from models import Secret
from serialization import model_to_dict
from template_status import get_template_link_info

from . import main_bp
from .crud_factory import EntityRouteConfig, register_standard_crud_routes


# Create bulk editor handler for secrets
_bulk_editor = create_secret_bulk_handler()


def update_secret_definitions_cid():
    """Update the secret definitions CID after secret changes."""
    return store_secret_definitions_cid()


def list_secrets():
    """Return all stored secrets."""
    return get_secrets()


def _build_secrets_editor_payload(secret_list: List[Secret]) -> str:
    """Return a JSON string representing the user's secrets for the editor."""
    return _bulk_editor.build_payload(secret_list)


def _parse_secrets_editor_payload(raw_payload: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """Validate and normalize the JSON payload supplied by the bulk editor."""
    return _bulk_editor.parse_payload(raw_payload)


def _apply_secrets_editor_changes(desired_values: Dict[str, str], existing: List[Secret]) -> None:
    """Persist the desired secrets, replacing the current collection."""
    _bulk_editor.apply_changes(desired_values, existing)


def _build_secrets_list_context(secrets_list: list) -> Dict[str, str]:
    """Build extra context for secrets list view."""
    context = {}
    if secrets_list:
        context['secret_definitions_cid'] = get_current_secret_definitions_cid()
    return context


# Configure and register standard CRUD routes using the factory
_secret_config = EntityRouteConfig(
    entity_class=Secret,
    entity_type='secret',
    plural_name='secrets',
    get_by_name_func=get_secret_by_name,
    get_entities_func=get_secrets,
    form_class=SecretForm,
    update_cid_func=update_secret_definitions_cid,
    to_json_func=model_to_dict,
    build_list_context=_build_secrets_list_context,
    form_template='secret_form.html',
    get_templates_func=get_template_secrets,
)

register_standard_crud_routes(main_bp, _secret_config)


@main_bp.route('/secrets/_/edit', methods=['GET', 'POST'])
def bulk_edit_secrets():
    """Edit all secrets at once using a JSON payload."""

    secrets_list = list_secrets()
    form = BulkSecretsForm()

    if request.method == 'GET':
        form.secrets_json.data = _build_secrets_editor_payload(secrets_list)

    if form.validate_on_submit():
        payload = form.secrets_json.data or ''
        normalized, error = _parse_secrets_editor_payload(payload)
        if error:
            form.secrets_json.errors.append(error)
        else:
            _apply_secrets_editor_changes(normalized, secrets_list)
            update_secret_definitions_cid()
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


__all__ = [
    'bulk_edit_secrets',
    'update_secret_definitions_cid',
    'list_secrets',
]
