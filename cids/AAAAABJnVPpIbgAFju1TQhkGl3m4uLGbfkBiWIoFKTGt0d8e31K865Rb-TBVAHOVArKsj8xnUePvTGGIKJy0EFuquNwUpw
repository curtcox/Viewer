# ruff: noqa: F821, F706
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_auth_header(email: str, api_token: str) -> str:
    token = base64.b64encode(f"{email}/token:{api_token}".encode()).decode()
    return f"Basic {token}"


def _build_preview(
    *,
    subdomain: str,
    operation: str,
    ticket_id: Optional[int],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = f"https://{subdomain}.zendesk.com/api/v2/tickets"
    url = f"{base_url}.json"
    method = "GET"

    if operation == "get_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}.json"
    elif operation == "create_ticket":
        method = "POST"

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
    subdomain: str,
    *,
    operation: str = "list_tickets",
    ticket_id: Optional[int] = None,
    subject: str = "",
    comment: str = "",
    status: str = "",
    priority: str = "",
    tags: Optional[list[str]] = None,
    email: str = "",
    ZENDESK_API_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Zendesk tickets."""

    if not subdomain:
        return validation_error("Missing required subdomain", field="subdomain")
    if not email:
        return validation_error("Missing required email", field="email")
    if not ZENDESK_API_TOKEN:
        return error_output(
            "Missing ZENDESK_API_TOKEN",
            status_code=401,
            details="Provide a Zendesk API token for Basic authentication",
        )

    normalized_operation = operation.lower()
    if normalized_operation not in {"list_tickets", "get_ticket", "create_ticket"}:
        return validation_error("Unsupported operation", field="operation")

    if normalized_operation == "create_ticket":
        if not subject:
            return validation_error("Missing required subject", field="subject")
        if not comment:
            return validation_error("Missing required comment", field="comment")
    if normalized_operation == "get_ticket" and ticket_id is None:
        return validation_error("Missing required ticket_id", field="ticket_id")

    headers = {
        "Authorization": _build_auth_header(email, ZENDESK_API_TOKEN),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{subdomain}.zendesk.com/api/v2/tickets"
    url = f"{base_url}.json"
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "get_ticket" and ticket_id is not None:
        url = f"{base_url}/{ticket_id}.json"
    elif normalized_operation == "create_ticket":
        payload = {
            "ticket": {
                "subject": subject,
                "comment": {"body": comment},
            }
        }
        if status:
            payload["ticket"]["status"] = status
        if priority:
            payload["ticket"]["priority"] = priority
        if tags:
            payload["ticket"]["tags"] = tags

    if dry_run:
        preview = _build_preview(
            subdomain=subdomain,
            operation=normalized_operation,
            ticket_id=ticket_id,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT

    try:
        if normalized_operation == "create_ticket":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Zendesk request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        message = data.get("error") or data.get("description") or "Zendesk API error"
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
