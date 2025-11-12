"""Server management routes and helpers."""

import json
import re
from collections.abc import Iterable
from typing import Any

from constants import ActionType, EntityType, ServerMode
from flask import abort, jsonify, redirect, render_template, request, url_for

from cid_presenter import cid_path, format_cid, format_cid_short
from cid_utils import (
    generate_cid,
    get_current_server_definitions_cid,
    store_server_definitions_cid,
)
from db_access import (
    create_cid_record,
    get_cid_by_path,
    get_server_by_name,
    get_user_secrets,
    get_user_server_invocations_by_server,
    get_user_servers,
    get_user_template_servers,
    get_user_uploads,
    get_user_variables,
)
from entity_references import extract_references_from_text
from forms import ServerForm
from identity import current_user
from interaction_log import load_interaction_history
from models import Server
from serialization import model_to_dict
from server_execution import analyze_server_definition, describe_main_function_parameters
from server_templates import get_server_templates
from syntax_highlighting import highlight_source

from . import main_bp
from .core import derive_name_from_path
from .crud_factory import EntityRouteConfig, register_standard_crud_routes
from .entities import create_entity, update_entity
from .history import _load_request_referers
from .server_definition_parser import ServerDefinitionParser


def _extract_context_references(
    definition: str | None,
    known_variables: Iterable[str] | None = None,
    known_secrets: Iterable[str] | None = None,
) -> dict[str, list[str]]:
    """Return referenced variable and secret names from a server definition."""
    if not definition:
        return {'variables': [], 'secrets': []}

    # Extract parameter names if available
    parameter_names = None
    description = describe_main_function_parameters(definition)
    if description:
        parameter_names = {
            str(parameter.get('name'))
            for parameter in description.get('parameters', [])
            if isinstance(parameter, dict) and parameter.get('name')
        }

    parser = ServerDefinitionParser()
    return parser.extract_context_references(
        definition,
        known_variables=known_variables,
        known_secrets=known_secrets,
        parameter_names=parameter_names
    )


def _extract_route_references(definition: str | None) -> list[str]:
    """Return route-like paths referenced within the server definition."""
    parser = ServerDefinitionParser()
    return parser.extract_route_references(definition)


def _build_server_test_config(server_name: str | None, definition: str | None):
    """Create the context needed to render the server test form."""

    if not server_name:
        return None

    action_path = f"/{server_name}"
    description = describe_main_function_parameters(definition or "")

    if description:
        return {
            'mode': ServerMode.MAIN.value,
            'action': action_path,
            'parameters': description.get('parameters', []),
        }

    return {
        'mode': ServerMode.QUERY.value,
        'action': action_path,
    }


def _sanitize_formdown_identifier(value: str) -> str:
    """Return a safe identifier for formdown form IDs."""

    candidate = (value or '').strip()
    if not candidate:
        return 'server-test-form'

    sanitized = re.sub(r'[^a-zA-Z0-9_-]+', '-', candidate)
    sanitized = re.sub(r'-{2,}', '-', sanitized).strip('-')
    return sanitized or 'server-test-form'


def _escape_formdown_attribute(value: str) -> str:
    """Escape attribute values for inclusion in formdown markup."""

    if value is None:
        return ''

    text = str(value)
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.replace('\n', '\\n')


def _render_server_test_formdown(server: Server, config: dict[str, object], defaults: dict[str, str]) -> str:
    """Build the formdown document that mirrors the inline server test form."""

    if not server or not config:
        return ''

    action = str(config.get('action') or f'/{server.name}')
    mode = (config.get('mode') or ServerMode.QUERY.value).lower()
    form_id = _sanitize_formdown_identifier(f"{server.name}-test-page")

    normalized_defaults: dict[str, str] = {}
    for key, value in (defaults or {}).items():
        if value is None:
            continue
        normalized_defaults[str(key)] = str(value)

    lines = [
        f"# Test page for /{server.name}",
        '',
        "This page mirrors the inline test form so you can save or reuse the same inputs later.",
        '',
        '```formdown',
        f"@form[id=\"{form_id}\" action=\"{_escape_formdown_attribute(action)}\" method=\"get\"]",
        '',
    ]

    if mode == ServerMode.MAIN.value:
        parameters = config.get('parameters') or []
        if parameters:
            lines.extend(['## Parameters', ''])
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            name = parameter.get('name')
            if not name:
                continue
            label = str(name)
            placeholder = f"Value for {label}"
            value_attr = ''
            existing_value = normalized_defaults.get(str(name), '')
            if existing_value != '':
                value_attr = f' value=\"{_escape_formdown_attribute(existing_value)}\"'
            help_text = 'Required parameter.' if parameter.get('required') else 'Optional parameter.'
            attributes = (
                f'text placeholder=\"{_escape_formdown_attribute(placeholder)}\"'
                f'{value_attr} help=\"{_escape_formdown_attribute(help_text)}\"'
            )
            lines.append(f"@{name}({label}): [{attributes}]")
    else:
        lines.extend(['## Query Parameters', ''])
        query_value = normalized_defaults.get('query', '')
        value_attr = ''
        if query_value != '':
            value_attr = f' value=\"{_escape_formdown_attribute(query_value)}\"'
        textarea_attributes = (
            f'textarea rows=4 placeholder=\"key=value\"{value_attr} '
            f'help=\"Enter one key=value pair per line.\"'
        )
        lines.append(f"@query_parameters(Query parameters): [{textarea_attributes}]")

    lines.extend([
        '',
        '@submit_test: [submit label="Run Test"]',
        '@reset_form: [reset label="Clear Inputs"]',
        '```',
        '',
        f"Submitting this form sends a GET request to `{action}` using your server's current definition.",
    ])

    return '\n'.join(lines).strip() + '\n'


def _highlight_definition_content(definition: str | None, history, server_name: str):
    """Return highlighted content for the current definition and history entries."""

    highlighted_definition = None
    syntax_css = None

    if definition:
        highlighted_definition, syntax_css = highlight_source(
            definition,
            filename=f"{server_name}.py",
            fallback_lexer='python',
        )

    for entry in history or []:
        highlighted, css = highlight_source(
            entry.get('definition'),
            filename=f"{server_name}.py",
            fallback_lexer='python',
        )
        entry['highlighted_definition'] = highlighted
        if not syntax_css and css:
            syntax_css = css

    return highlighted_definition, syntax_css


@main_bp.route('/servers/validate-definition', methods=['POST'])
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


@main_bp.route('/servers/<server_name>/upload-test-page', methods=['POST'])
def upload_server_test_page(server_name):
    """Persist a formdown page that mirrors the inline server test form."""

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    test_config = _build_server_test_config(server.name, server.definition)
    if not test_config:
        response = jsonify({'error': 'Test form is not available for this server.'})
        response.status_code = 400
        return response

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        payload = {}

    defaults: dict[str, str] = {}
    values = payload.get('values')
    if isinstance(values, dict):
        for key, value in values.items():
            if value is None:
                continue
            defaults[str(key)] = str(value)

    mode = (test_config.get('mode') or 'query').lower()
    if mode == ServerMode.MAIN.value:
        allowed_names = {
            str(parameter.get('name'))
            for parameter in test_config.get('parameters') or []
            if isinstance(parameter, dict) and parameter.get('name')
        }
        defaults = {key: value for key, value in defaults.items() if key in allowed_names}
    else:
        query_value = ''
        if isinstance(values, dict) and 'query' in values and values.get('query') is not None:
            query_value = str(values.get('query'))
        defaults = {'query': query_value}

    document = _render_server_test_formdown(server, test_config, defaults)
    if not document:
        response = jsonify({'error': 'Unable to generate formdown content.'})
        response.status_code = 400
        return response

    content_bytes = document.encode('utf-8')
    cid_value = format_cid(generate_cid(content_bytes))
    record_path = cid_path(cid_value)
    existing = get_cid_by_path(record_path) if record_path else None
    if not existing:
        create_cid_record(cid_value, content_bytes, current_user.id)

    redirect_url = cid_path(cid_value, 'md.html')
    response = jsonify({'redirect_url': redirect_url, 'cid': cid_value})
    response.status_code = 200
    return response


def _parse_server_snapshot(cid, server_name: str) -> dict[str, Any] | None:
    """Parse a server definition snapshot from a CID record.

    Args:
        cid: CID record containing server definitions
        server_name: Name of the server to extract

    Returns:
        dict: Parsed snapshot data, or None if parsing fails
    """
    try:
        content = cid.file_data.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return None

    try:
        server_definitions = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(server_definitions, dict) or server_name not in server_definitions:
        return None

    definition_text = server_definitions[server_name]
    definition_bytes = definition_text.encode('utf-8')
    per_server_cid = format_cid(generate_cid(definition_bytes))

    snapshot_cid = format_cid(cid.path)
    snapshot_path = cid_path(snapshot_cid) if snapshot_cid else None

    return {
        'definition': definition_text,
        'definition_cid': per_server_cid,
        'snapshot_cid': snapshot_cid,
        'snapshot_path': snapshot_path,
        'created_at': cid.created_at,
        'is_current': False,
    }


def get_server_definition_history(user_id, server_name):
    """Get historical server definitions for a specific server.

    Args:
        user_id: User ID to get history for
        server_name: Name of the server

    Returns:
        list: History of server definitions, most recent first
    """
    cids = get_user_uploads(user_id)

    history = []

    try:
        iterator = iter(cids)
    except TypeError:
        return history

    for cid in iterator:
        snapshot = _parse_server_snapshot(cid, server_name)
        if snapshot:
            history.append(snapshot)

    if history:
        history[0]['is_current'] = True

    return history


def update_server_definitions_cid(user_id):
    """Update the server definitions CID after server changes."""
    return store_server_definitions_cid(user_id)


def user_servers():
    return get_user_servers(current_user.id)


def _build_reference_links(entity_type: str, names: list[str]) -> list[dict[str, str]]:
    """Build link dictionaries for entity references.

    Args:
        entity_type: Type of entity ('variable' or 'secret')
        names: List of entity names

    Returns:
        list: Link dictionaries with 'label' and 'url' keys
    """
    return [
        {
            'label': name,
            'url': url_for(f'main.view_{entity_type}', **{f'{entity_type}_name': name}),
        }
        for name in names
    ]


def _build_route_links(paths: list[str]) -> list[dict[str, str]]:
    """Build link dictionaries for route references.

    Args:
        paths: List of route paths

    Returns:
        list: Link dictionaries with 'label' and 'url' keys
    """
    return [
        {
            'label': path,
            'url': path,
        }
        for path in paths
    ]


def _build_server_row(
    server,
    known_variables: set[str],
    known_secrets: set[str]
) -> dict[str, object]:
    """Build display data for a single server row.

    Args:
        server: Server model instance
        known_variables: Set of known variable names
        known_secrets: Set of known secret names

    Returns:
        dict: Server row data with references
    """
    definition_text = getattr(server, 'definition', '')
    context_refs = _extract_context_references(
        definition_text,
        known_variables=known_variables,
        known_secrets=known_secrets,
    )
    route_refs = _extract_route_references(definition_text)

    return {
        'server': server,
        'variables': _build_reference_links('variable', context_refs.get('variables', [])),
        'secrets': _build_reference_links('secret', context_refs.get('secrets', [])),
        'routes': _build_route_links(route_refs),
    }


def _get_known_entity_names(user_id: str) -> tuple[set[str], set[str]]:
    """Get sets of known variable and secret names for the user.

    Args:
        user_id: User ID

    Returns:
        tuple: (known_variable_names, known_secret_names)
    """
    known_variable_names = {
        str(variable.name)
        for variable in get_user_variables(user_id)
        if getattr(variable, 'name', None)
    }
    known_secret_names = {
        str(secret.name)
        for secret in get_user_secrets(user_id)
        if getattr(secret, 'name', None)
    }
    return known_variable_names, known_secret_names


def _build_servers_list_context(servers_list: list, user_id: str) -> dict[str, Any]:
    """Build extra context for servers list view.

    Args:
        servers_list: List of server entities
        user_id: User ID

    Returns:
        Dictionary with server-specific list view context
    """
    context = {}

    if servers_list:
        context['server_definitions_cid'] = format_cid(
            get_current_server_definitions_cid(user_id)
        )

        known_variables, known_secrets = _get_known_entity_names(user_id)

        server_rows = []
        for server in servers_list:
            server_rows.append(_build_server_row(server, known_variables, known_secrets))

        context['server_rows'] = server_rows

    return context


def _build_server_view_context(server: Server, user_id: str) -> dict[str, Any]:
    """Build extra context for server detail view.

    Args:
        server: Server entity
        user_id: User ID

    Returns:
        Dictionary with server-specific detail view context
    """
    history = get_server_definition_history(user_id, server.name)
    invocations = get_server_invocation_history(user_id, server.name)
    test_config = _build_server_test_config(server.name, server.definition)

    highlighted_definition, syntax_css = _highlight_definition_content(
        server.definition,
        history,
        server.name,
    )

    definition_references = extract_references_from_text(
        getattr(server, 'definition', ''),
        user_id,
    )

    test_interactions = []
    if test_config and test_config.get('action'):
        test_interactions = load_interaction_history(
            user_id,
            EntityType.SERVER_TEST.value,
            test_config.get('action'),
        )

    return {
        'definition_history': history,
        'server_invocations': invocations,
        'server_invocation_count': len(invocations),
        'server_test_config': test_config,
        'server_test_interactions': test_interactions,
        'highlighted_definition': highlighted_definition,
        'syntax_css': syntax_css,
        'definition_references': definition_references,
    }


# Configure and register standard CRUD routes using the factory
_server_config = EntityRouteConfig(
    entity_class=Server,
    entity_type='server',
    plural_name='servers',
    get_by_name_func=get_server_by_name,
    get_user_entities_func=get_user_servers,
    form_class=ServerForm,
    update_cid_func=update_server_definitions_cid,
    to_json_func=lambda s: model_to_dict(s),
    build_list_context=_build_servers_list_context,
    build_view_context=_build_server_view_context,
)

register_standard_crud_routes(main_bp, _server_config)


@main_bp.route('/servers/new', methods=['GET', 'POST'])
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

    user_server_templates = [
        {
            'id': f'user-{server.id}',
            'name': server.name,
            'definition': server.definition or '',
            'suggested_name': f"{server.name}-copy" if server.name else '',
        }
        for server in get_user_template_servers(current_user.id)
    ]

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
    interaction_history = load_interaction_history(current_user.id, EntityType.SERVER.value, entity_name_hint)

    return render_template(
        'server_form.html',
        form=form,
        title='Create New Server',
        server_templates=get_server_templates(),
        user_server_templates=user_server_templates,
        server=None,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
        server_test_interactions=[],
    )


@main_bp.route('/servers/<server_name>/edit', methods=['GET', 'POST'])
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

    _, syntax_css = _highlight_definition_content(
        server.definition,
        history,
        server.name,
    )

    change_message = (request.form.get('change_message') or '').strip()
    definition_text_current = form.definition.data or server.definition or ''

    server_interactions = load_interaction_history(current_user.id, EntityType.SERVER.value, server.name)
    test_interactions = []
    if test_config and test_config.get('action'):
        test_interactions = load_interaction_history(
            current_user.id,
            EntityType.SERVER_TEST.value,
            test_config.get('action'),
        )

    upload_url = url_for('main.upload_server_test_page', server_name=server.name)

    if form.validate_on_submit():
        save_action = (request.form.get('submit_action') or '').strip().lower()
        if save_action == ActionType.SAVE_AS.value:
            if create_entity(
                Server,
                form,
                current_user.id,
                'server',
                change_message=change_message,
                content_text=definition_text_current,
            ):
                return redirect(url_for('main.view_server', server_name=form.name.data))
        else:
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
            syntax_css=syntax_css,
            server_test_upload_url=upload_url,
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
        syntax_css=syntax_css,
        server_test_upload_url=upload_url,
    )


def get_server_invocation_history(user_id, server_name):
    """Return invocation events for a specific server ordered from newest to oldest."""
    invocations = get_user_server_invocations_by_server(user_id, server_name)

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
    'edit_server',
    'get_server_definition_history',
    'get_server_invocation_history',
    'new_server',
    'update_server_definitions_cid',
    'user_servers',
    'upload_server_test_page',
    'validate_server_definition',
]
