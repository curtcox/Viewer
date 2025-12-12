"""Server invocation record creation and tracking."""

import json
from typing import Optional, Union

from flask import request
from sqlalchemy.exc import SQLAlchemyError

from cid import CID as ValidatedCID
from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid, get_current_secret_definitions_cid, get_current_server_definitions_cid, get_current_variable_definitions_cid
from db_access import ServerInvocationInput, create_cid_record, create_server_invocation, get_cid_by_path, save_entity
from models import ServerInvocation


def request_details():
    """Collect request details for server execution context."""
    try:
        json_body = request.get_json(silent=True)
    except (UnicodeDecodeError, ValueError):
        json_body = None

    try:
        raw_body = request.get_data(cache=True)
    except Exception:  # pragma: no cover - defensive fallback for unexpected request failures
        raw_body = b""

    body_text: Optional[str] = None
    if raw_body:
        try:
            body_text = raw_body.decode("utf-8")
        except UnicodeDecodeError:
            body_text = raw_body.decode("utf-8", errors="replace")

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
        "json": json_body,
        "body": body_text,
    }


def _normalize_cid_input(value: Union[str, ValidatedCID, None]) -> str:
    """Return a normalized CID string from a string or ValidatedCID input."""
    if isinstance(value, ValidatedCID):
        return value.value
    return value or ""


def create_server_invocation_record(
    server_name: str,
    result_cid: Union[str, ValidatedCID],
    *,
    external_calls: Optional[list[dict[str, object]]] = None,
) -> Optional[ServerInvocation]:
    """Create a ServerInvocation record and persist related metadata."""
    servers_cid = get_current_server_definitions_cid()
    variables_cid = get_current_variable_definitions_cid()
    secrets_cid = get_current_secret_definitions_cid()

    try:
        req_json = json.dumps(request_details(), indent=2, sort_keys=True)
        req_bytes = req_json.encode("utf-8")
        req_cid_value = format_cid(generate_cid(req_bytes))
        req_cid_path = cid_path(req_cid_value)
        if req_cid_path and not get_cid_by_path(req_cid_path):
            create_cid_record(req_cid_value, req_bytes)
        req_cid = req_cid_value if req_cid_path else None
    except (TypeError, ValueError, SQLAlchemyError, OSError):
        # Handle JSON serialization, CID generation, or database errors
        req_cid = None

    calls_cid: Optional[str] = None
    if external_calls is not None:
        try:
            calls_json = json.dumps(external_calls, indent=2, sort_keys=True)
            calls_bytes = calls_json.encode("utf-8")
            calls_cid_value = format_cid(generate_cid(calls_bytes))
            calls_cid_path = cid_path(calls_cid_value)
            if calls_cid_path and not get_cid_by_path(calls_cid_path):
                create_cid_record(calls_cid_value, calls_bytes)
            calls_cid = calls_cid_value if calls_cid_path else None
        except (TypeError, ValueError, SQLAlchemyError, OSError):
            calls_cid = None

    invocation = create_server_invocation(
        server_name,
        result_cid,
        ServerInvocationInput(
            servers_cid=servers_cid,
            variables_cid=variables_cid,
            secrets_cid=secrets_cid,
            request_details_cid=req_cid,
            external_calls_cid=calls_cid,
        ),
    )

    try:
        inv_payload = {
            "server_name": server_name,
            "result_cid": _normalize_cid_input(result_cid),
            "servers_cid": servers_cid,
            "variables_cid": variables_cid,
            "secrets_cid": secrets_cid,
            "request_details_cid": req_cid,
            "external_calls_cid": calls_cid,
            "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
        }
        inv_json = json.dumps(inv_payload, indent=2, sort_keys=True)
        inv_bytes = inv_json.encode("utf-8")
        inv_cid_value = format_cid(generate_cid(inv_bytes))
        inv_cid_path = cid_path(inv_cid_value)
        if inv_cid_path and not get_cid_by_path(inv_cid_path):
            create_cid_record(inv_cid_value, inv_bytes)

        invocation.invocation_cid = inv_cid_value if inv_cid_path else None
        save_entity(invocation)
    except (TypeError, ValueError, AttributeError, SQLAlchemyError, OSError):
        # Ignore errors when storing invocation metadata
        pass

    return invocation
