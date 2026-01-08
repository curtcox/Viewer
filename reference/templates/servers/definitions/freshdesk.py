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
    "list_tickets": OperationDefinition(),
    "get_ticket": OperationDefinition(
        required=(RequiredField("ticket_id"),),
    ),
    "create_ticket": OperationDefinition(
        required=(
            RequiredField("subject"),
            RequiredField("description"),
            RequiredField("email"),
        ),
        payload_builder=lambda subject, description, email, status, priority, **_: {
            "subject": subject,
            "description": description,
            "email": email,
            "status": status,
            "priority": priority,
        },
    ),
    "update_ticket": OperationDefinition(
        required=(RequiredField("ticket_id"),),
        payload_builder=lambda subject, description, status, priority, **_: {
            key: value
            for key, value in {
                "subject": subject or None,
                "description": description or None,
                "status": status if status else None,
                "priority": priority if priority else None,
            }.items()
            if value is not None
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_tickets": lambda **_: "tickets",
    "get_ticket": lambda ticket_id, **_: f"tickets/{ticket_id}",
    "create_ticket": lambda **_: "tickets",
    "update_ticket": lambda ticket_id, **_: f"tickets/{ticket_id}",
}

_METHODS = {
    "create_ticket": "POST",
    "update_ticket": "PUT",
}


def _build_auth_header(api_key: str) -> str:
    """Build Basic Auth header with API key as username."""
    token = base64.b64encode(f"{api_key}:X".encode()).decode()
    return f"Basic {token}"


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "basic",
    }
    if payload:
        preview["payload"] = payload

    return preview


def _freshdesk_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("description") or data.get("errors") or "Freshdesk API error"
    return "Freshdesk API error"


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

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        email=email,
        status=status,
        priority=priority,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": _build_auth_header(FRESHDESK_API_KEY),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{domain}.freshdesk.com/api/v2"
    endpoint = _ENDPOINT_BUILDERS[operation](ticket_id=ticket_id)
    url = f"{base_url}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
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
        error_parser=_freshdesk_error_message,
        request_error_message="Freshdesk request failed",
        include_exception_in_message=False,
    )
