"""Server management routes and helpers."""

from typing import Optional

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_presenter import cid_path, format_cid, format_cid_short
from cid_utils import (
    generate_cid,
    get_current_server_definitions_cid,
    store_server_definitions_cid,
)
from db_access import delete_entity, get_server_by_name, get_user_servers
from forms import ServerForm
from models import CID, Server, ServerInvocation
from server_execution import analyze_server_definition, describe_main_function_parameters
from server_templates import get_server_templates
from interaction_log import load_interaction_history

from . import main_bp
from .core import derive_name_from_path
from .entities import create_entity, update_entity
from .history import _load_request_referers


def _build_server_test_config(server_name: Optional[str], definition: Optional[str]):
    """Create the context needed to render the server test form."""

    if not server_name:
        return None

    action_path = f"/{server_name}"
    description = describe_main_function_parameters(definition or "")

    if description:
        return {
            'mode': 'main',
            'action': action_path,
            'parameters': description.get('parameters', []),
        }

    return {
        'mode': 'query',
        'action': action_path,
    }


@main_bp.route('/servers/validate-definition', methods=['POST'])
@require_login
def validate_server_definition():
    """Validate a server definition and report auto main compatibility."""

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        response = jsonify({'error': 'Request body must be JSON.'})
        response.status_code = 400
        return response

    definition = payload.get('definition')
    if not isinstance(definition, str):
        response = jsonify({'error': 'Definition must be provided as a string.'})
        response.status_code = 400
        return response

    analysis = analyze_server_definition(definition)
    return jsonify(analysis)


def get_server_definition_history(user_id, server_name):
    """Get historical server definitions for a specific server."""
    from models import db

    cids = (
        db.session.query(CID)
        .filter(CID.uploaded_by_user_id == user_id)
        .order_by(CID.created_at.desc())
        .all()
    )

    history = []

    try:
        iterator = iter(cids)
    except TypeError:
        return history

    for cid in iterator:
        try:
            content = cid.file_data.decode('utf-8')

            try:
                import json

                server_definitions = json.loads(content)

                if isinstance(server_definitions, dict) and server_name in server_definitions:
                    definition_text = server_definitions[server_name]
                    definition_bytes = definition_text.encode('utf-8')
                    per_server_cid = format_cid(generate_cid(definition_bytes))

                    snapshot_cid = format_cid(cid.path)
                    snapshot_path = cid_path(snapshot_cid) if snapshot_cid else None

                    history.append(
                        {
                            'definition': definition_text,
                            'definition_cid': per_server_cid,
                            'snapshot_cid': snapshot_cid,
                            'snapshot_path': snapshot_path,
                            'created_at': cid.created_at,
                            'is_current': False,
                        }
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        except (UnicodeDecodeError, AttributeError):
            continue

    if history:
        history[0]['is_current'] = True

    return history


def update_server_definitions_cid(user_id):
    """Update the server definitions CID after server changes."""
    return store_server_definitions_cid(user_id)


def user_servers():
    return get_user_servers(current_user.id)


@main_bp.route('/servers')
@require_login
def servers():
    """Display user's servers."""
    servers_list = user_servers()
    server_definitions_cid = None
    if servers_list:
        server_definitions_cid = format_cid(
            get_current_server_definitions_cid(current_user.id)
        )

    return render_template(
        'servers.html',
        servers=servers_list,
        server_definitions_cid=server_definitions_cid,
    )


@main_bp.route('/servers/new', methods=['GET', 'POST'])
@require_login
def new_server():
    """Create a new server."""
    form = ServerForm()

    if request.method == 'GET':
        path_hint = request.args.get('path', '')
        suggested_name = derive_name_from_path(path_hint)
        if suggested_name and not form.name.data:
            form.name.data = suggested_name

    change_message = (request.form.get('change_message') or '').strip()
    definition_text = form.definition.data or ''

    if form.validate_on_submit():
        if create_entity(
            Server,
            form,
            current_user.id,
            'server',
            change_message=change_message,
            content_text=definition_text,
        ):
            return redirect(url_for('main.servers'))

    entity_name_hint = (form.name.data or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'server', entity_name_hint)

    return render_template(
        'server_form.html',
        form=form,
        title='Create New Server',
        server_templates=get_server_templates(),
        server=None,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
        server_test_interactions=[],
    )


@main_bp.route('/servers/<server_name>')
@require_login
def view_server(server_name):
    """View a specific server."""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    history = get_server_definition_history(current_user.id, server_name)
    invocations = get_server_invocation_history(current_user.id, server_name)
    test_config = _build_server_test_config(server.name, server.definition)

    test_interactions = []
    if test_config and test_config.get('action'):
        test_interactions = load_interaction_history(
            current_user.id,
            'server-test',
            test_config.get('action'),
        )

    return render_template(
        'server_view.html',
        server=server,
        definition_history=history,
        server_invocations=invocations,
        server_invocation_count=len(invocations),
        server_test_config=test_config,
        server_test_interactions=test_interactions,
    )


@main_bp.route('/servers/<server_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_server(server_name):
    """Edit a specific server."""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    form = ServerForm(obj=server)

    history = get_server_definition_history(current_user.id, server_name)
    invocations = get_server_invocation_history(current_user.id, server_name)
    definition_text = form.definition.data if form.definition.data is not None else server.definition
    test_config = _build_server_test_config(server.name, definition_text)

    change_message = (request.form.get('change_message') or '').strip()
    definition_text_current = form.definition.data or server.definition or ''

    server_interactions = load_interaction_history(current_user.id, 'server', server.name)
    test_interactions = []
    if test_config and test_config.get('action'):
        test_interactions = load_interaction_history(
            current_user.id,
            'server-test',
            test_config.get('action'),
        )

    if form.validate_on_submit():
        if update_entity(
            server,
            form,
            'server',
            change_message=change_message,
            content_text=definition_text_current,
        ):
            return redirect(url_for('main.view_server', server_name=server.name))
        return render_template(
            'server_form.html',
            form=form,
            title=f'Edit Server "{server.name}"',
            server=server,
            definition_history=history,
            server_invocations=invocations,
            server_invocation_count=len(invocations),
            server_test_config=test_config,
            interaction_history=server_interactions,
            ai_entity_name=server.name,
            ai_entity_name_field=form.name.id,
            server_test_interactions=test_interactions,
        )

    return render_template(
        'server_form.html',
        form=form,
        title=f'Edit Server "{server.name}"',
        server=server,
        definition_history=history,
        server_invocations=invocations,
        server_invocation_count=len(invocations),
        server_test_config=test_config,
        interaction_history=server_interactions,
        ai_entity_name=server.name,
        ai_entity_name_field=form.name.id,
        server_test_interactions=test_interactions,
    )


@main_bp.route('/servers/<server_name>/delete', methods=['POST'])
@require_login
def delete_server(server_name):
    """Delete a specific server."""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    user_id = server.user_id
    delete_entity(server)

    update_server_definitions_cid(user_id)

    flash(f'Server "{server_name}" deleted successfully!', 'success')
    return redirect(url_for('main.servers'))


def get_server_invocation_history(user_id, server_name):
    """Return invocation events for a specific server ordered from newest to oldest."""
    invocations = (
        ServerInvocation.query
        .filter(
            ServerInvocation.user_id == user_id,
            ServerInvocation.server_name == server_name,
        )
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )

    if not invocations:
        return []

    referer_by_request = _load_request_referers(invocations)

    for invocation in invocations:
        invocation.invocation_link = cid_path(
            getattr(invocation, 'invocation_cid', None),
            'json',
        )
        invocation.invocation_label = format_cid_short(
            getattr(invocation, 'invocation_cid', None)
        )
        invocation.request_details_link = cid_path(
            getattr(invocation, 'request_details_cid', None),
            'json',
        )
        invocation.request_details_label = format_cid_short(
            getattr(invocation, 'request_details_cid', None)
        )
        invocation.result_link = cid_path(
            getattr(invocation, 'result_cid', None),
            'txt',
        )
        invocation.result_label = format_cid_short(
            getattr(invocation, 'result_cid', None)
        )
        invocation.servers_cid_link = cid_path(
            getattr(invocation, 'servers_cid', None),
            'json',
        )
        invocation.servers_cid_label = format_cid_short(
            getattr(invocation, 'servers_cid', None)
        )

        request_cid = getattr(invocation, 'request_details_cid', None)
        invocation.request_referer = (
            referer_by_request.get(request_cid)
            if request_cid
            else None
        )

    return invocations


__all__ = [
    'delete_server',
    'edit_server',
    'get_server_definition_history',
    'get_server_invocation_history',
    'new_server',
    'servers',
    'update_server_definitions_cid',
    'user_servers',
    'view_server',
    'validate_server_definition',
]
