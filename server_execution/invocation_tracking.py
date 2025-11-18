"""Server invocation record creation and tracking."""

import json
from typing import Optional

from flask import request
from sqlalchemy.exc import SQLAlchemyError

from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid, get_current_secret_definitions_cid, get_current_server_definitions_cid, get_current_variable_definitions_cid
from db_access import ServerInvocationInput, create_cid_record, create_server_invocation, get_cid_by_path, save_entity
from models import ServerInvocation


def request_details():
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


def create_server_invocation_record(server_name: str, result_cid: str) -> Optional[ServerInvocation]:
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

    invocation = create_server_invocation(
        server_name,
        result_cid,
        ServerInvocationInput(
            servers_cid=servers_cid,
            variables_cid=variables_cid,
            secrets_cid=secrets_cid,
            request_details_cid=req_cid,
        ),
    )

    try:
        inv_payload = {
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
