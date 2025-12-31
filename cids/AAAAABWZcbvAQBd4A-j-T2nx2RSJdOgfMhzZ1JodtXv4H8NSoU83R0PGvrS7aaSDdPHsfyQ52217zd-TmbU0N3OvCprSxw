# ruff: noqa: F821, F706
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_auth_header(username: str, password: str) -> str:
    """Build Basic Auth header with username and password."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _build_preview(
    *,
    instance: str,
    operation: str,
    table: str,
    sys_id: Optional[str],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = f"https://{instance}.service-now.com/api/now/table/{table}"
    url = base_url
    method = "GET"

    if operation == "get_record" and sys_id:
        url = f"{base_url}/{sys_id}"
    elif operation == "create_record":
        method = "POST"
    elif operation == "update_record" and sys_id:
        url = f"{base_url}/{sys_id}"
        method = "PUT"

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

    normalized_operation = operation.lower()
    valid_operations = {"list_records", "get_record", "create_record", "update_record"}
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    if normalized_operation in {"get_record", "update_record"}:
        if not sys_id:
            return validation_error("Missing required sys_id", field="sys_id")

    if normalized_operation == "create_record":
        if not short_description:
            return validation_error("Missing required short_description", field="short_description")

    headers = {
        "Authorization": _build_auth_header(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{instance}.service-now.com/api/now/table/{table}"
    url = base_url
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "get_record" and sys_id:
        url = f"{base_url}/{sys_id}"
    elif normalized_operation == "create_record":
        payload = {
            "short_description": short_description,
        }
        if description:
            payload["description"] = description
        if urgency:
            payload["urgency"] = urgency
        if impact:
            payload["impact"] = impact
    elif normalized_operation == "update_record" and sys_id:
        url = f"{base_url}/{sys_id}"
        payload = {}
        if short_description:
            payload["short_description"] = short_description
        if description:
            payload["description"] = description
        if urgency:
            payload["urgency"] = urgency
        if impact:
            payload["impact"] = impact

    if dry_run:
        preview = _build_preview(
            instance=instance,
            operation=normalized_operation,
            table=table,
            sys_id=sys_id,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT

    try:
        if normalized_operation == "create_record":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif normalized_operation == "update_record":
            response = api_client.put(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("ServiceNow request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        message = data.get("error") or data.get("message") or "ServiceNow API error"
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
