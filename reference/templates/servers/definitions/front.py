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
    "send_message": OperationDefinition(
        required=(
            RequiredField("channel_id"),
            RequiredField("to"),
            RequiredField("body"),
        ),
        payload_builder=lambda to, body, subject, **_: {
            "to": to,
            "body": body,
            **({"subject": subject} if subject else {}),
        },
    ),
    "list_teammates": OperationDefinition(),
    "get_teammate": OperationDefinition(
        required=(RequiredField("teammate_id"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_conversations": lambda **_: "conversations",
    "get_conversation": lambda conversation_id, **_: f"conversations/{conversation_id}",
    "send_message": lambda channel_id, **_: f"channels/{channel_id}/messages",
    "list_teammates": lambda **_: "teammates",
    "get_teammate": lambda teammate_id, **_: f"teammates/{teammate_id}",
}

_METHODS = {
    "send_message": "POST",
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


def _front_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("message") or data.get("_error") or "Front API error"
    return "Front API error"


def main(
    *,
    operation: str = "list_conversations",
    conversation_id: Optional[str] = None,
    teammate_id: Optional[str] = None,
    channel_id: str = "",
    to: Optional[list[str]] = None,
    subject: str = "",
    body: str = "",
    FRONT_API_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Front conversations and teammates."""

    if not FRONT_API_TOKEN:
        return error_output(
            "Missing FRONT_API_TOKEN",
            status_code=401,
            details="Provide a Front API token for Bearer authentication",
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        conversation_id=conversation_id,
        teammate_id=teammate_id,
        channel_id=channel_id,
        to=to,
        subject=subject,
        body=body,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    headers = {
        "Authorization": f"Bearer {FRONT_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = "https://api2.frontapp.com"
    endpoint = _ENDPOINT_BUILDERS[operation](
        conversation_id=conversation_id,
        channel_id=channel_id,
        teammate_id=teammate_id,
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
        error_parser=_front_error_message,
        request_error_message="Front request failed",
        include_exception_in_message=False,
    )
