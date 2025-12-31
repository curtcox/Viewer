# ruff: noqa: F821, F706
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_auth_header(api_key: str) -> str:
    """Build Basic Auth header with API key as username."""
    token = base64.b64encode(f"{api_key}:X".encode()).decode()
    return f"Basic {token}"


def _build_preview(
    *,
    domain: str,
    operation: str,
    ticket_id: Optional[int],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = f"https://{domain}.freshdesk.com/api/v2/tickets"
    url = f"{base_url}"
    method = "GET"

    if operation == "get_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}"
    elif operation == "create_ticket":
        method = "POST"
    elif operation == "update_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}"
        method = "PUT"

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "basic",
    }
    if payload:
        preview["payload"] = payload

    return preview


def main(
    domain: str,
    *,
    operation: str = "list_tickets",
    ticket_id: Optional[int] = None,
    subject: str = "",
    description: str = "",
    email: str = "",
    status: int = 2,
    priority: int = 1,
    FRESHDESK_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Freshdesk tickets."""

    if not domain:
        return validation_error("Missing required domain", field="domain")
    if not FRESHDESK_API_KEY:
        return error_output(
            "Missing FRESHDESK_API_KEY",
            status_code=401,
            details="Provide a Freshdesk API key for Basic authentication",
        )

    normalized_operation = operation.lower()
    valid_operations = {"list_tickets", "get_ticket", "create_ticket", "update_ticket"}
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    if normalized_operation in {"get_ticket", "update_ticket"}:
        if ticket_id is None:
            return validation_error("Missing required ticket_id", field="ticket_id")

    if normalized_operation == "create_ticket":
        if not subject:
            return validation_error("Missing required subject", field="subject")
        if not description:
            return validation_error("Missing required description", field="description")
        if not email:
            return validation_error("Missing required email", field="email")

    headers = {
        "Authorization": _build_auth_header(FRESHDESK_API_KEY),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{domain}.freshdesk.com/api/v2/tickets"
    url = base_url
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "get_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}"
    elif normalized_operation == "create_ticket":
        payload = {
            "subject": subject,
            "description": description,
            "email": email,
            "status": status,
            "priority": priority,
        }
    elif normalized_operation == "update_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}"
        payload = {}
        if subject:
            payload["subject"] = subject
        if description:
            payload["description"] = description
        if status:
            payload["status"] = status
        if priority:
            payload["priority"] = priority

    if dry_run:
        preview = _build_preview(
            domain=domain,
            operation=normalized_operation,
            ticket_id=ticket_id,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT

    try:
        if normalized_operation == "create_ticket":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif normalized_operation == "update_ticket":
            response = api_client.put(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Freshdesk request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        message = data.get("description") or data.get("errors") or "Freshdesk API error"
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
