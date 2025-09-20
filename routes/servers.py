"""Server management routes and helpers."""
from textwrap import dedent

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_utils import (
    generate_cid,
    get_current_server_definitions_cid,
    store_server_definitions_cid,
)
from db_access import delete_entity, get_server_by_name, get_user_servers
from forms import ServerForm
from models import CID, Server, ServerInvocation

from . import main_bp
from .entities import create_entity, update_entity


SERVER_TEMPLATES = [
    {
        'id': 'echo',
        'name': 'Echo request context',
        'description': 'Render the incoming request and context as HTML for debugging.',
        'definition': dedent(
            """
            from html import escape

            def dict_to_html_ul(data: dict) -> str:
                if not isinstance(data, dict):
                    raise TypeError("expects a dict at the top level")

                def render(d: dict) -> str:
                    items = d.items()

                    lis = []
                    for k, v in items:
                        k_html = escape(str(k))
                        if isinstance(v, dict):
                            lis.append(f"<li>{k_html}{render(v)}</li>")
                        else:
                            v_html = "" if v is None else escape(str(v))
                            lis.append(f"<li>{k_html}: {v_html}</li>")
                    return "<ul>" + "".join(lis) + "</ul>"

                return render(data)

            out = {
              'request': request,
              'context': context
            }

            html = '<html><body>' + dict_to_html_ul(out) + '</body></html>'

            return { 'output': html }
            """
        ).strip(),
    },
    {
        'id': 'openrouter',
        'name': 'OpenRouter API call',
        'description': 'Call the OpenRouter chat completions API with a sample prompt.',
        'definition': dedent(
            """
            import os
            import requests

            API_KEY = os.getenv("OPENROUTER_API_KEY")
            if not API_KEY:
                raise RuntimeError("Set the OPENROUTER_API_KEY environment variable.")

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "nvidia/nemotron-nano-9b-v2:free",
                "messages": [
                    {"role": "user", "content": "What is the meaning of life?"}
                ]
            }

            resp = requests.post(url, headers=headers, json=data, timeout=60)
            resp.raise_for_status()

            return { 'output': resp.json() }
            """
        ).strip(),
    },
]


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
                    per_server_cid = generate_cid(definition_bytes)

                    snapshot_cid_no_slash = cid.path[1:] if cid.path.startswith('/') else cid.path

                    history.append(
                        {
                            'definition': definition_text,
                            'definition_cid': per_server_cid,
                            'snapshot_cid': snapshot_cid_no_slash,
                            'snapshot_path': cid.path,
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
        server_definitions_cid = get_current_server_definitions_cid(current_user.id)

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

    if form.validate_on_submit():
        if create_entity(Server, form, current_user.id, 'server'):
            return redirect(url_for('main.servers'))

    return render_template(
        'server_form.html',
        form=form,
        title='Create New Server',
        server_templates=SERVER_TEMPLATES,
    )


@main_bp.route('/servers/<server_name>')
@require_login
def view_server(server_name):
    """View a specific server."""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    history = get_server_definition_history(current_user.id, server_name)
    invocations = get_server_invocation_extremes(current_user.id, server_name)

    return render_template(
        'server_view.html',
        server=server,
        definition_history=history,
        server_invocations=invocations,
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
    invocations = get_server_invocation_extremes(current_user.id, server_name)

    if form.validate_on_submit():
        if update_entity(server, form, 'server'):
            return redirect(url_for('main.view_server', server_name=server.name))
        return render_template(
            'server_form.html',
            form=form,
            title=f'Edit Server "{server.name}"',
            server=server,
            definition_history=history,
            server_invocations=invocations,
        )

    return render_template(
        'server_form.html',
        form=form,
        title=f'Edit Server "{server.name}"',
        server=server,
        definition_history=history,
        server_invocations=invocations,
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


def _invocation_to_dict(inv):
    return {
        'result_cid': inv.result_cid,
        'invoked_at': inv.invoked_at,
        'servers_cid': inv.servers_cid,
        'variables_cid': inv.variables_cid,
        'secrets_cid': inv.secrets_cid,
        'request_details_cid': getattr(inv, 'request_details_cid', None),
        'invocation_cid': getattr(inv, 'invocation_cid', None),
    }


def get_server_invocation_extremes(user_id, server_name):
    """Return first 3 and last 3 invocations for a server name (by time)."""
    base_query = ServerInvocation.query.filter_by(user_id=user_id, server_name=server_name)
    total = base_query.count()
    result = {'total_count': total}

    if total == 0:
        return result

    if total < 7:
        all_inv = base_query.order_by(
            ServerInvocation.invoked_at.asc(),
            ServerInvocation.id.asc(),
        ).all()
        result['all_invocations'] = [_invocation_to_dict(i) for i in all_inv]
        return result

    first_three = base_query.order_by(
        ServerInvocation.invoked_at.asc(),
        ServerInvocation.id.asc(),
    ).limit(3).all()
    last_three = base_query.order_by(
        ServerInvocation.invoked_at.desc(),
        ServerInvocation.id.desc(),
    ).limit(3).all()

    result['first_invocations'] = [_invocation_to_dict(i) for i in first_three]
    result['last_invocations'] = [_invocation_to_dict(i) for i in last_three]
    return result


__all__ = [
    'delete_server',
    'edit_server',
    'get_server_definition_history',
    'get_server_invocation_extremes',
    'new_server',
    'servers',
    'update_server_definitions_cid',
    'user_servers',
    'view_server',
]
