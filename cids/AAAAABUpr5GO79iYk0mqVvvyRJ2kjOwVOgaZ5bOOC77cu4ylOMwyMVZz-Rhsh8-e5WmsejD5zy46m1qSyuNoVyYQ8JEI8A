# ruff: noqa: F821, F706
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_records": OperationDefinition(),
    "get_record": OperationDefinition(
        required=(RequiredField("sys_id"),),
    ),
    "create_record": OperationDefinition(
        required=(RequiredField("short_description"),),
        payload_builder=lambda short_description, description, urgency, impact, **_: {
            "short_description": short_description,
            **({"description": description} if description else {}),
            **({"urgency": urgency} if urgency else {}),
            **({"impact": impact} if impact else {}),
        },
    ),
    "update_record": OperationDefinition(
        required=(RequiredField("sys_id"),),
        payload_builder=lambda short_description, description, urgency, impact, **_: {
            **({"short_description": short_description} if short_description else {}),
            **({"description": description} if description else {}),
            **({"urgency": urgency} if urgency else {}),
            **({"impact": impact} if impact else {}),
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_records": lambda base_url, **_: base_url,
    "get_record": lambda base_url, sys_id, **_: f"{base_url}/{sys_id}",
    "create_record": lambda base_url, **_: base_url,
    "update_record": lambda base_url, sys_id, **_: f"{base_url}/{sys_id}",
}

_METHODS = {
    "create_record": "POST",
    "update_record": "PUT",
}


def _build_auth_header(username: str, password: str) -> str:
    """Build Basic Auth header with username and password."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    table: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "basic",
        "table": table,
    }
    if payload:
        preview["payload"] = payload

    return preview


def _servicenow_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        error_block = data.get("error")
        if isinstance(error_block, dict):
            return (
                error_block.get("message")
                or error_block.get("detail")
                or "ServiceNow API error"
            )
        if isinstance(error_block, str):
            return error_block
        return data.get("message") or "ServiceNow API error"
    return "ServiceNow API error"


def main(
    instance: str,
    *,
    operation: str = "list_records",
    table: str = "incident",
    sys_id: Optional[str] = None,
    short_description: str = "",
    description: str = "",
    urgency: str = "",
    impact: str = "",
    SERVICENOW_USERNAME: str = "",
    SERVICENOW_PASSWORD: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with ServiceNow records."""

    if not instance:
        return validation_error("Missing required instance", field="instance")
    if not table:
        return validation_error("Missing required table", field="table")
    if not SERVICENOW_USERNAME:
        return validation_error("Missing required SERVICENOW_USERNAME", field="SERVICENOW_USERNAME")
    if not SERVICENOW_PASSWORD:
        return error_output(
            "Missing SERVICENOW_PASSWORD",
            status_code=401,
            details="Provide a ServiceNow password for Basic authentication",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        sys_id=sys_id,
        short_description=short_description,
        description=description,
        urgency=urgency,
        impact=impact,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": _build_auth_header(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{instance}.service-now.com/api/now/table/{table}"
    url = _ENDPOINT_BUILDERS[operation](base_url=base_url, sys_id=sys_id)
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            table=table,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT
    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_servicenow_error_message,
        request_error_message="ServiceNow request failed",
    )
