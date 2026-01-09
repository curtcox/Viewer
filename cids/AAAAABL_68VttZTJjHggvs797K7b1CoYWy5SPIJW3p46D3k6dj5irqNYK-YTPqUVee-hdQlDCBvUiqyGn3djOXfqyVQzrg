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
    "reply_to_conversation": OperationDefinition(
        required=(
            RequiredField("conversation_id"),
            RequiredField("admin_id"),
            RequiredField("message"),
        ),
        payload_builder=lambda admin_id, message, **_: {
            "message_type": "comment",
            "type": "admin",
            "admin_id": admin_id,
            "body": message,
        },
    ),
    "list_contacts": OperationDefinition(),
    "get_contact": OperationDefinition(
        required=(RequiredField("contact_id"),),
    ),
    "create_contact": OperationDefinition(
        required=(RequiredField("email"),),
        payload_builder=lambda email, name, role, **_: {
            "email": email,
            **({"name": name} if name else {}),
            **({"role": role} if role else {}),
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_conversations": lambda **_: "conversations",
    "get_conversation": lambda conversation_id, **_: f"conversations/{conversation_id}",
    "reply_to_conversation": lambda conversation_id, **_: f"conversations/{conversation_id}/reply",
    "list_contacts": lambda **_: "contacts",
    "get_contact": lambda contact_id, **_: f"contacts/{contact_id}",
    "create_contact": lambda **_: "contacts",
}

_METHODS = {
    "reply_to_conversation": "POST",
    "create_contact": "POST",
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


def _intercom_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        errors = data.get("errors")
        if isinstance(errors, list) and errors:
            message = errors[0].get("message")
            if message:
                return message
        return "Intercom API error"
    return "Intercom API error"


def main(
    *,
    operation: str = "list_conversations",
    conversation_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    admin_id: Optional[str] = None,
    message: str = "",
    email: str = "",
    name: str = "",
    role: str = "",
    INTERCOM_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Intercom conversations and contacts."""

    if not INTERCOM_ACCESS_TOKEN:
        return error_output(
            "Missing INTERCOM_ACCESS_TOKEN",
            status_code=401,
            details="Provide an Intercom access token for Bearer authentication",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        conversation_id=conversation_id,
        contact_id=contact_id,
        admin_id=admin_id,
        message=message,
        email=email,
        name=name,
        role=role,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": f"Bearer {INTERCOM_ACCESS_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    base_url = "https://api.intercom.io"
    endpoint = _ENDPOINT_BUILDERS[operation](
        conversation_id=conversation_id,
        contact_id=contact_id,
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
        error_parser=_intercom_error_message,
        request_error_message="Intercom request failed",
        include_exception_in_message=False,
    )
