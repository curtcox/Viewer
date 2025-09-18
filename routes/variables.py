"""Variable management routes and helpers."""
from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_utils import (
    get_current_variable_definitions_cid,
    store_variable_definitions_cid,
)
from db_access import delete_entity, get_user_variables, get_variable_by_name
from forms import VariableForm
from models import Variable

from . import main_bp
from .entities import create_entity, update_entity


def update_variable_definitions_cid(user_id):
    """Update the variable definitions CID after variable changes."""
    return store_variable_definitions_cid(user_id)


def user_variables():
    return get_user_variables(current_user.id)


@main_bp.route('/variables')
@require_login
def variables():
    """Display user's variables."""
    variables_list = user_variables()
    variable_definitions_cid = None
    if variables_list:
        variable_definitions_cid = get_current_variable_definitions_cid(current_user.id)
    return render_template(
        'variables.html',
        variables=variables_list,
        variable_definitions_cid=variable_definitions_cid,
    )


@main_bp.route('/variables/new', methods=['GET', 'POST'])
@require_login
def new_variable():
    """Create a new variable."""
    form = VariableForm()

    if form.validate_on_submit():
        if create_entity(Variable, form, current_user.id, 'variable'):
            return redirect(url_for('main.variables'))

    return render_template('variable_form.html', form=form, title='Create New Variable')


@main_bp.route('/variables/<variable_name>')
@require_login
def view_variable(variable_name):
    """View a specific variable."""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    return render_template('variable_view.html', variable=variable)


@main_bp.route('/variables/<variable_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_variable(variable_name):
    """Edit a specific variable."""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    form = VariableForm(obj=variable)

    if form.validate_on_submit():
        if update_entity(variable, form, 'variable'):
            return redirect(url_for('main.view_variable', variable_name=variable.name))
        return render_template(
            'variable_form.html',
            form=form,
            title=f'Edit Variable "{variable.name}"',
            variable=variable,
        )

    return render_template(
        'variable_form.html',
        form=form,
        title=f'Edit Variable "{variable.name}"',
        variable=variable,
    )


@main_bp.route('/variables/<variable_name>/delete', methods=['POST'])
@require_login
def delete_variable(variable_name):
    """Delete a specific variable."""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    delete_entity(variable)
    update_variable_definitions_cid(current_user.id)

    flash(f'Variable "{variable_name}" deleted successfully!', 'success')
    return redirect(url_for('main.variables'))


__all__ = [
    'delete_variable',
    'edit_variable',
    'new_variable',
    'update_variable_definitions_cid',
    'user_variables',
    'variables',
    'view_variable',
]
