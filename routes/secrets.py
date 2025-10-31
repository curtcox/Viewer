"""Secret management routes and helpers."""
from typing import Dict

from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for

from cid_utils import (
    get_current_secret_definitions_cid,
    store_secret_definitions_cid,
)
from db_access import delete_entity, get_secret_by_name, get_user_secrets
from forms import SecretForm
from identity import current_user
from interaction_log import load_interaction_history
from models import Secret
from serialization import model_to_dict

from . import main_bp
from .entities import create_entity, update_entity


def update_secret_definitions_cid(user_id):
    """Update the secret definitions CID after secret changes."""
    return store_secret_definitions_cid(user_id)


def user_secrets():
    return get_user_secrets(current_user.id)


@main_bp.route('/secrets')
def secrets():
    """Display user's secrets."""
    secrets_list = user_secrets()
    secret_definitions_cid = None
    if secrets_list:
        secret_definitions_cid = get_current_secret_definitions_cid(current_user.id)
    if _wants_json_response():
        return jsonify([_secret_to_json(secret) for secret in secrets_list])
    return render_template(
        'secrets.html',
        secrets=secrets_list,
        secret_definitions_cid=secret_definitions_cid,
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

    if _wants_json_response():
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
    'delete_secret',
    'edit_secret',
    'new_secret',
    'secrets',
    'update_secret_definitions_cid',
    'user_secrets',
    'view_secret',
]
def _wants_json_response() -> bool:
    return getattr(g, "response_format", None) == "json"


def _secret_to_json(secret: Secret) -> Dict[str, object]:
    return model_to_dict(secret)

