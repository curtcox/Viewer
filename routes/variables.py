"""Variable management routes and helpers."""
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional, Tuple

from flask import abort, flash, redirect, render_template, request, url_for

from cid_utils import (
    get_current_variable_definitions_cid,
    store_variable_definitions_cid,
)
from db_access import delete_entity, get_user_variables, get_variable_by_name
from forms import VariableForm
from identity import current_user
from interaction_log import load_interaction_history
from models import Variable

from . import main_bp
from .entities import create_entity, update_entity
from .meta import inspect_path_metadata


def update_variable_definitions_cid(user_id):
    """Update the variable definitions CID after variable changes."""
    return store_variable_definitions_cid(user_id)


def user_variables():
    return get_user_variables(current_user.id)


def _status_label(status: int) -> Optional[str]:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return None


def _format_status(status: int) -> str:
    label = _status_label(status)
    return f"{status} – {label}" if label else str(status)


def _append_detail(details: List[Dict[str, str]], label: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    if isinstance(value, list):
        if not value:
            return
        rendered = ", ".join(str(item) for item in value)
    elif isinstance(value, bool):
        rendered = "Yes" if value else "No"
    else:
        rendered = str(value)
    details.append({"label": label, "value": rendered})


def _describe_route_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    endpoint = resolution.get("endpoint")
    rule = resolution.get("rule")
    if endpoint and rule:
        summary = f"Route {endpoint} ({rule})"
    elif endpoint:
        summary = f"Route {endpoint}"
    elif rule:
        summary = f"Route {rule}"
    else:
        summary = "Route"
    _append_detail(details, "Endpoint", endpoint)
    _append_detail(details, "Rule", rule)
    _append_detail(details, "Blueprint", resolution.get("blueprint"))
    methods = resolution.get("methods")
    if methods:
        _append_detail(details, "Methods", ", ".join(methods))
    return summary, details


def _describe_alias_redirect_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    alias_name = resolution.get("alias")
    target_path = resolution.get("target_path")
    if alias_name and target_path:
        summary = f"Alias {alias_name} → {target_path}"
    elif alias_name:
        summary = f"Alias {alias_name}"
    elif target_path:
        summary = f"Alias redirect to {target_path}"
    else:
        summary = "Alias redirect"
    _append_detail(details, "Alias", alias_name)
    _append_detail(details, "Target", target_path)
    redirect_location = resolution.get("redirect_location")
    if redirect_location and redirect_location != target_path:
        _append_detail(details, "Redirect Location", redirect_location)
    target_metadata = resolution.get("target_metadata") or {}
    target_status = target_metadata.get("status_code")
    if target_status is not None:
        _append_detail(details, "Target Status", _format_status(target_status))
    resolved_path = target_metadata.get("path")
    if resolved_path and resolved_path != target_path:
        _append_detail(details, "Resolved Path", resolved_path)
    return summary, details


def _describe_server_execution_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    server_name = resolution.get("server_name")
    summary = f"Server {server_name}" if server_name else "Server execution"
    function_name = resolution.get("function_name")
    if resolution.get("type") == "server_function_execution" and function_name:
        summary = f"{summary}.{function_name}"
        _append_detail(details, "Function", function_name)
    _append_detail(details, "Server", server_name)
    requires_auth = resolution.get("requires_authentication")
    if requires_auth is not None:
        _append_detail(details, "Requires Authentication", requires_auth)
    return summary, details


def _describe_versioned_server_execution_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    server_name = resolution.get("server_name")
    partial = resolution.get("partial_cid")
    summary = "Versioned server"
    if server_name:
        summary = f"{summary} {server_name}"
    if partial:
        summary = f"{summary} @ {partial}"
    function_name = resolution.get("function_name")
    if resolution.get("type") == "versioned_server_function_execution" and function_name:
        summary = f"{summary}.{function_name}"
        _append_detail(details, "Function", function_name)
    _append_detail(details, "Server", server_name)
    _append_detail(details, "Partial CID", partial)
    matches = resolution.get("matches")
    if isinstance(matches, list):
        _append_detail(details, "Matches", len(matches))
    return summary, details


def _describe_cid_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    cid_value = resolution.get("cid")
    summary = f"CID {cid_value}" if cid_value else "CID content"
    _append_detail(details, "CID", cid_value)
    _append_detail(details, "Extension", resolution.get("extension"))
    return summary, details


def _describe_method_not_allowed_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    allowed = resolution.get("allowed_methods") or []
    summary = "Method not allowed"
    if allowed:
        _append_detail(details, "Allowed Methods", ", ".join(allowed))
    return summary, details


def _describe_redirect_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    details: List[Dict[str, str]] = []
    location = resolution.get("location")
    summary = f"Redirect to {location}" if location else "Redirect"
    _append_detail(details, "Location", location)
    return summary, details


_RESOLUTION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Tuple[str, List[Dict[str, str]]]]] = {
    "route": _describe_route_resolution,
    "alias_redirect": _describe_alias_redirect_resolution,
    "server_execution": _describe_server_execution_resolution,
    "server_function_execution": _describe_server_execution_resolution,
    "versioned_server_execution": _describe_versioned_server_execution_resolution,
    "versioned_server_function_execution": _describe_versioned_server_execution_resolution,
    "cid": _describe_cid_resolution,
    "method_not_allowed": _describe_method_not_allowed_resolution,
    "redirect": _describe_redirect_resolution,
}


def _describe_resolution(resolution: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    rtype = resolution.get("type") or ""
    handler = _RESOLUTION_HANDLERS.get(rtype)
    if handler:
        return handler(resolution)
    if rtype:
        return rtype.replace("_", " ").title(), []
    return "Unknown resolution", []


def build_matching_route_info(value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not value or not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate.startswith("/"):
        return None

    metadata, status = inspect_path_metadata(
        candidate,
        include_alias_relations=False,
        include_alias_target_metadata=True,
    )

    info: Dict[str, Any] = {
        "path": candidate,
        "status": status,
        "status_label": _status_label(status),
        "summary": "No matching route.",
        "details": [],
        "resolution_type": None,
    }

    if not metadata:
        return info

    resolution = metadata.get("resolution") or {}
    summary, details = _describe_resolution(resolution)
    info.update(
        {
            "summary": summary,
            "details": details,
            "resolution_type": resolution.get("type"),
        }
    )
    return info


@main_bp.route('/variables')
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
def new_variable():
    """Create a new variable."""
    form = VariableForm()

    change_message = (request.form.get('change_message') or '').strip()
    definition_text = form.definition.data or ''

    if form.validate_on_submit():
        if create_entity(
            Variable,
            form,
            current_user.id,
            'variable',
            change_message=change_message,
            content_text=definition_text,
        ):
            return redirect(url_for('main.variables'))

    entity_name_hint = (form.name.data or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'variable', entity_name_hint)

    return render_template(
        'variable_form.html',
        form=form,
        title='Create New Variable',
        variable=None,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
        matching_route=None,
    )


@main_bp.route('/variables/<variable_name>')
def view_variable(variable_name):
    """View a specific variable."""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    matching_route = build_matching_route_info(variable.definition)

    return render_template(
        'variable_view.html',
        variable=variable,
        matching_route=matching_route,
    )


@main_bp.route('/variables/<variable_name>/edit', methods=['GET', 'POST'])
def edit_variable(variable_name):
    """Edit a specific variable."""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    form = VariableForm(obj=variable)

    change_message = (request.form.get('change_message') or '').strip()
    definition_text = form.definition.data or variable.definition or ''

    interaction_history = load_interaction_history(current_user.id, 'variable', variable.name)

    current_definition = form.definition.data
    if current_definition is None:
        current_definition = variable.definition
    matching_route = build_matching_route_info(current_definition)

    if form.validate_on_submit():
        if update_entity(
            variable,
            form,
            'variable',
            change_message=change_message,
            content_text=definition_text,
        ):
            return redirect(url_for('main.view_variable', variable_name=variable.name))
        return render_template(
            'variable_form.html',
            form=form,
            title=f'Edit Variable "{variable.name}"',
            variable=variable,
            interaction_history=interaction_history,
            ai_entity_name=variable.name,
            ai_entity_name_field=form.name.id,
            matching_route=matching_route,
        )

    return render_template(
        'variable_form.html',
        form=form,
        title=f'Edit Variable "{variable.name}"',
        variable=variable,
        interaction_history=interaction_history,
        ai_entity_name=variable.name,
        ai_entity_name_field=form.name.id,
        matching_route=matching_route,
    )


@main_bp.route('/variables/<variable_name>/delete', methods=['POST'])
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
