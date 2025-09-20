"""Helper functions for executing user-defined servers."""

import json
import traceback
from typing import Any, Callable, Dict, Iterable, Optional

from flask import jsonify, make_response, redirect, render_template, request
from flask_login import current_user

from cid_utils import (
    generate_cid,
    get_current_secret_definitions_cid,
    get_current_server_definitions_cid,
    get_current_variable_definitions_cid,
    get_extension_from_mime_type,
)
from db_access import (
    create_cid_record,
    create_server_invocation,
    get_cid_by_path,
    get_server_by_name,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    save_entity,
)
from text_function_runner import run_text_function


def model_as_dict(model_objects: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """Convert SQLAlchemy model objects to a name->definition mapping."""
    if not model_objects:
        return {}

    result: Dict[str, Any] = {}
    for obj in model_objects:
        if hasattr(obj, "name") and hasattr(obj, "definition"):
            result[obj.name] = obj.definition
        else:
            result[str(obj)] = str(obj)
    return result


def request_details() -> Dict[str, Any]:
    """Collect request details for server execution context."""
    return {
        "path": request.path,
        "query_string": request.query_string.decode("utf-8"),
        "remote_addr": request.remote_addr,
        "user_agent": request.user_agent.string,
        "headers": {k: v for k, v in request.headers if k.lower() != "cookie"},
        "form_data": dict(request.form) if request.form else {},
        "args": dict(request.args) if request.args else {},
        "endpoint": request.endpoint,
        "scheme": request.scheme,
        "host": request.host,
        "method": request.method,
    }


def _load_user_context() -> Dict[str, Dict[str, Any]]:
    if not getattr(current_user, "is_authenticated", False):
        return {"variables": {}, "secrets": {}, "servers": {}}

    user_id = getattr(current_user, "id", None)
    if not user_id:
        return {"variables": {}, "secrets": {}, "servers": {}}

    variables = model_as_dict(get_user_variables(user_id))
    secrets = model_as_dict(get_user_secrets(user_id))
    servers = model_as_dict(get_user_servers(user_id))
    return {"variables": variables, "secrets": secrets, "servers": servers}


def build_request_args() -> Dict[str, Any]:
    """Build the argument payload supplied to user-defined server code."""
    return {
        "request": request_details(),
        "context": _load_user_context(),
    }


def create_server_invocation_record(user_id: str, server_name: str, result_cid: str):
    """Create a ServerInvocation record and persist related metadata."""
    servers_cid = get_current_server_definitions_cid(user_id)
    variables_cid = get_current_variable_definitions_cid(user_id)
    secrets_cid = get_current_secret_definitions_cid(user_id)

    try:
        req_json = json.dumps(request_details(), indent=2, sort_keys=True)
        req_bytes = req_json.encode("utf-8")
        req_cid = generate_cid(req_bytes)
        if not get_cid_by_path(f"/{req_cid}"):
            create_cid_record(req_cid, req_bytes, user_id)
    except Exception:
        req_cid = None

    invocation = create_server_invocation(
        user_id,
        server_name,
        result_cid,
        servers_cid=servers_cid,
        variables_cid=variables_cid,
        secrets_cid=secrets_cid,
        request_details_cid=req_cid,
        invocation_cid=None,
    )

    try:
        inv_payload = {
            "user_id": user_id,
            "server_name": server_name,
            "result_cid": result_cid,
            "servers_cid": servers_cid,
            "variables_cid": variables_cid,
            "secrets_cid": secrets_cid,
            "request_details_cid": req_cid,
            "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
        }
        inv_json = json.dumps(inv_payload, indent=2, sort_keys=True)
        inv_bytes = inv_json.encode("utf-8")
        inv_cid = generate_cid(inv_bytes)
        if not get_cid_by_path(f"/{inv_cid}"):
            create_cid_record(inv_cid, inv_bytes, user_id)

        invocation.invocation_cid = inv_cid
        save_entity(invocation)
    except Exception:
        pass

    return invocation


def _encode_output(output: Any) -> bytes:
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode("utf-8")
    # Dicts -> JSON for human-friendly output instead of concatenated keys
    if isinstance(output, dict):
        try:
            return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        except Exception:
            return str(output).encode("utf-8")
    # If it's an iterable, try to handle common patterns gracefully
    try:
        from collections.abc import Iterable as _Iterable  # local import to avoid top changes
        if isinstance(output, _Iterable):
            items = list(output)
            # If elements look JSON-serializable (e.g., list of dicts), prefer JSON
            try:
                if items and any(isinstance(x, (dict, list, tuple)) for x in items):
                    return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            except Exception as json_err:
                print(f"[server_execution] JSON encoding attempt failed: {type(json_err).__name__}: {json_err}")
                print(f"[server_execution] Output type: {type(output).__name__}")
                print(f"[server_execution] Items types: {[type(x).__name__ for x in items[:5]]}...")
                traceback.print_exc()
                # Continue to try other encodings
            # List of ints -> bytes directly
            if all(isinstance(x, int) for x in items):
                return bytes(items)
            # List of bytes -> concatenate
            if all(isinstance(x, bytes) for x in items):
                return b"".join(items)
            # List of strings -> join then encode
            if all(isinstance(x, str) for x in items):
                return "".join(items).encode("utf-8")
    except Exception:
        # fall back below
        pass

    # Fallback: encode the string representation
    return str(output).encode("utf-8")


def execute_server_code(server, server_name: str):
    """Execute server code and return a redirect to the resulting CID."""
    code = server.definition
    args = build_request_args()

    try:
        result = run_text_function(code, args)
        output = result.get("output", "")
        content_type = result.get("content_type", "text/html")
        # Debug info to console
        try:
            sample = repr(output)
            if sample and len(sample) > 300:
                sample = sample[:300] + "…"
            print(
                f"[server_execution] execute_server_code: output_type={type(output).__name__}, "
                f"content_type={content_type}, sample={sample}"
            )
        except Exception as debug_err:
            print(f"[server_execution] Debug output failed: {type(debug_err).__name__}: {debug_err}")
            traceback.print_exc()

        output_bytes = _encode_output(output)
        cid = generate_cid(output_bytes)

        existing = get_cid_by_path(f"/{cid}")
        if not existing:
            create_cid_record(cid, output_bytes, current_user.id)

        create_server_invocation_record(current_user.id, server_name, cid)

        extension = get_extension_from_mime_type(content_type)
        if extension:
            return redirect(f"/{cid}.{extension}")
        return redirect(f"/{cid}")
    except Exception as exc:
        text = (
            str(exc)
            + "\n\n"
            + traceback.format_exc()
            + "\n\n"
            + code
            + "\n\n"
            + str(args)
        )
        response = make_response(text)
        response.headers["Content-Type"] = "text/plain"
        response.status_code = 500
        return response


def execute_server_code_from_definition(definition_text: str, server_name: str):
    """Execute server code from a supplied historical definition."""
    code = definition_text
    args = build_request_args()

    try:
        result = run_text_function(code, args)
        output = result.get("output", "")
        content_type = result.get("content_type", "text/html")
        # Debug info to console
        try:
            sample = repr(output)
            if sample and len(sample) > 300:
                sample = sample[:300] + "…"
            print(
                f"[server_execution] execute_server_code_from_definition: output_type={type(output).__name__}, "
                f"content_type={content_type}, sample={sample}"
            )
        except Exception as debug_err:
            print(f"[server_execution] Debug output failed in _from_definition: {type(debug_err).__name__}: {debug_err}")
            traceback.print_exc()

        output_bytes = _encode_output(output)
        cid = generate_cid(output_bytes)

        existing = get_cid_by_path(f"/{cid}")
        if not existing:
            create_cid_record(cid, output_bytes, current_user.id)

        create_server_invocation_record(current_user.id, server_name, cid)

        extension = get_extension_from_mime_type(content_type)
        if extension:
            return redirect(f"/{cid}.{extension}")
        return redirect(f"/{cid}")
    except Exception as exc:
        text = (
            str(exc)
            + "\n\n"
            + traceback.format_exc()
            + "\n\n"
            + code
            + "\n\n"
            + str(args)
        )
        response = make_response(text)
        response.headers["Content-Type"] = "text/plain"
        response.status_code = 500
        return response


def is_potential_versioned_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could represent /{server}/{partial_cid}."""
    if not path or not path.startswith("/"):
        return False
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) != 2:
        return False
    if f"/{parts[0]}" in existing_routes:
        return False
    return True


def try_server_execution_with_partial(
    path: str,
    history_fetcher: Callable[[str, str], Iterable[Dict[str, Any]]],
):
    """Execute a server version referenced by a partial CID."""
    if not getattr(current_user, "is_authenticated", False):
        return None

    parts = [segment for segment in path.split("/") if segment]
    if len(parts) != 2:
        return None
    server_name, partial = parts

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    history = history_fetcher(current_user.id, server_name)
    matches = [h for h in history if h.get("definition_cid", "").startswith(partial)]

    if not matches:
        return render_template("404.html", path=path), 404

    if len(matches) > 1:
        payload = {
            "error": "Multiple matching server versions",
            "server": server_name,
            "partial": partial,
            "matches": [
                {
                    "definition_cid": m.get("definition_cid"),
                    "snapshot_cid": m.get("snapshot_cid"),
                    "created_at": m.get("created_at").isoformat() if m.get("created_at") else None,
                }
                for m in matches
            ],
        }
        return jsonify(payload), 400

    definition_text = matches[0].get("definition", "")
    return execute_server_code_from_definition(definition_text, server_name)


def is_potential_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could map to a server name."""
    return path.startswith("/") and path.count("/") == 1 and path not in existing_routes


def try_server_execution(path: str):
    """Execute the server whose name matches the request path."""
    if not getattr(current_user, "is_authenticated", False):
        return None

    potential_server_name = path[1:]
    server = get_server_by_name(current_user.id, potential_server_name)
    if server:
        return execute_server_code(server, potential_server_name)
    return None
