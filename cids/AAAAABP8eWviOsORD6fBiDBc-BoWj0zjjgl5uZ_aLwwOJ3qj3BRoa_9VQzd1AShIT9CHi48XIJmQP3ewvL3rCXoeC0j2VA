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
            RequiredField("message"),
            RequiredField("customer_email"),
        ),
        payload_builder=lambda subject, message, customer_email, status, priority, **_: {
            "subject": subject,
            "messages": [
                {
                    "channel": "email",
                    "from_agent": False,
                    "body_text": message,
                    "sender": {"email": customer_email},
                }
            ],
            **({"status": status} if status else {}),
            **({"priority": priority} if priority else {}),
        },
    ),
    "update_ticket": OperationDefinition(
        required=(RequiredField("ticket_id"),),
        payload_builder=lambda subject, status, priority, **_: {
            key: value
            for key, value in {
                "subject": subject or None,
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


def _build_auth_header(email: str, api_key: str) -> str:
    """Build Basic Auth header with email and API key."""
    token = base64.b64encode(f"{email}:{api_key}".encode()).decode()
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


def _gorgias_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "Gorgias API error"
    return "Gorgias API error"


def main(
    domain: str,
    *,
    operation: str = "list_tickets",
    ticket_id: Optional[int] = None,
    subject: str = "",
    message: str = "",
    customer_email: str = "",
    status: str = "",
    priority: str = "",
    email: str = "",
    GORGIAS_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Gorgias tickets."""

    if not domain:
        return validation_error("Missing required domain", field="domain")
    if not email:
        return validation_error("Missing required email", field="email")
    if not GORGIAS_API_KEY:
        return error_output(
            "Missing GORGIAS_API_KEY",
            status_code=401,
            details="Provide a Gorgias API key for Basic authentication",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        ticket_id=ticket_id,
        subject=subject,
        message=message,
        customer_email=customer_email,
        status=status,
        priority=priority,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": _build_auth_header(email, GORGIAS_API_KEY),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{domain}.gorgias.com/api"
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
        error_parser=_gorgias_error_message,
        request_error_message="Gorgias request failed",
        include_exception_in_message=False,
    )
