"""Secret management routes and helpers."""
from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_utils import (
    get_current_secret_definitions_cid,
    store_secret_definitions_cid,
)
from db_access import delete_entity, get_secret_by_name, get_user_secrets
from forms import SecretForm
from models import Secret

from . import main_bp
from .entities import create_entity, update_entity


def update_secret_definitions_cid(user_id):
    """Update the secret definitions CID after secret changes."""
    return store_secret_definitions_cid(user_id)


def user_secrets():
    return get_user_secrets(current_user.id)


@main_bp.route('/secrets')
@require_login
def secrets():
    """Display user's secrets."""
    secrets_list = user_secrets()
    secret_definitions_cid = None
    if secrets_list:
        secret_definitions_cid = get_current_secret_definitions_cid(current_user.id)
    return render_template(
        'secrets.html',
        secrets=secrets_list,
        secret_definitions_cid=secret_definitions_cid,
    )


@main_bp.route('/secrets/new', methods=['GET', 'POST'])
@require_login
def new_secret():
    """Create a new secret."""
    form = SecretForm()

    if form.validate_on_submit():
        if create_entity(Secret, form, current_user.id, 'secret'):
            return redirect(url_for('main.secrets'))

    return render_template('secret_form.html', form=form, title='Create New Secret')


@main_bp.route('/secrets/<secret_name>')
@require_login
def view_secret(secret_name):
    """View a specific secret."""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    return render_template('secret_view.html', secret=secret)


@main_bp.route('/secrets/<secret_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_secret(secret_name):
    """Edit a specific secret."""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    form = SecretForm(obj=secret)

    if form.validate_on_submit():
        if update_entity(secret, form, 'secret'):
            return redirect(url_for('main.view_secret', secret_name=secret.name))
        return render_template(
            'secret_form.html',
            form=form,
            title=f'Edit Secret "{secret.name}"',
            secret=secret,
        )

    return render_template(
        'secret_form.html',
        form=form,
        title=f'Edit Secret "{secret.name}"',
        secret=secret,
    )


@main_bp.route('/secrets/<secret_name>/delete', methods=['POST'])
@require_login
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
