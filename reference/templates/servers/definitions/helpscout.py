# ruff: noqa: F821, F706
from __future__ import annotations

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
    "list_conversations": OperationDefinition(),
    "get_conversation": OperationDefinition(
        required=(RequiredField("conversation_id"),),
    ),
    "create_conversation": OperationDefinition(
        required=(
            RequiredField("mailbox_id"),
            RequiredField("subject"),
            RequiredField("customer_email"),
            RequiredField("text"),
        ),
        payload_builder=lambda mailbox_id, subject, customer_email, text, **_: {
            "subject": subject,
            "mailboxId": mailbox_id,
            "customer": {"email": customer_email},
            "threads": [
                {
                    "type": "customer",
                    "customer": {"email": customer_email},
                    "text": text,
                }
            ],
        },
    ),
    "list_customers": OperationDefinition(),
    "get_customer": OperationDefinition(
        required=(RequiredField("customer_id"),),
    ),
    "create_customer": OperationDefinition(
        required=(
            RequiredField("first_name"),
            RequiredField("last_name"),
            RequiredField("email"),
        ),
        payload_builder=lambda first_name, last_name, email, **_: {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_conversations": lambda **_: "conversations",
    "get_conversation": lambda conversation_id, **_: f"conversations/{conversation_id}",
    "create_conversation": lambda **_: "conversations",
    "list_customers": lambda **_: "customers",
    "get_customer": lambda customer_id, **_: f"customers/{customer_id}",
    "create_customer": lambda **_: "customers",
}

_METHODS = {
    "create_conversation": "POST",
    "create_customer": "POST",
}


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
        "auth": "bearer",
    }
    if payload:
        preview["payload"] = payload

    return preview


def _helpscout_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "Help Scout API error"
    return "Help Scout API error"


def main(
    *,
    operation: str = "list_conversations",
    conversation_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    mailbox_id: Optional[str] = None,
    subject: str = "",
    customer_email: str = "",
    text: str = "",
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    HELPSCOUT_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Help Scout conversations and customers."""

    if not HELPSCOUT_API_KEY:
        return error_output(
            "Missing HELPSCOUT_API_KEY",
            status_code=401,
            details="Provide a Help Scout API key for Bearer authentication",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        conversation_id=conversation_id,
        customer_id=customer_id,
        mailbox_id=mailbox_id,
        subject=subject,
        customer_email=customer_email,
        text=text,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": f"Bearer {HELPSCOUT_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = "https://api.helpscout.net/v2"
    endpoint = _ENDPOINT_BUILDERS[operation](
        conversation_id=conversation_id,
        customer_id=customer_id,
    )
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
        error_parser=_helpscout_error_message,
        request_error_message="Help Scout request failed",
    )
