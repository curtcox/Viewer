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
            RequiredField("comment"),
        ),
        payload_builder=lambda subject, comment, status, priority, tags, **_: {
            "ticket": {
                "subject": subject,
                "comment": {"body": comment},
                **({"status": status} if status else {}),
                **({"priority": priority} if priority else {}),
                **({"tags": tags} if tags else {}),
            }
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_tickets": lambda **_: "tickets.json",
    "get_ticket": lambda ticket_id, **_: f"tickets/{ticket_id}.json",
    "create_ticket": lambda **_: "tickets.json",
}

_METHODS = {
    "create_ticket": "POST",
}


def _build_auth_header(email: str, api_token: str) -> str:
    token = base64.b64encode(f"{email}/token:{api_token}".encode()).decode()
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


def _zendesk_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("error") or data.get("description") or "Zendesk API error"
    return "Zendesk API error"


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

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        ticket_id=ticket_id,
        subject=subject,
        comment=comment,
        status=status,
        priority=priority,
        tags=tags,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": _build_auth_header(email, ZENDESK_API_TOKEN),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{subdomain}.zendesk.com/api/v2"
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
        error_parser=_zendesk_error_message,
        request_error_message="Zendesk request failed",
        include_exception_in_message=False,
    )
