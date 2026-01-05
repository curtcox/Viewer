# ruff: noqa: F821, F706
from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    conversation_id: Optional[str],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = "https://api2.frontapp.com"
    
    if operation == "list_conversations":
        url = f"{base_url}/conversations"
        method = "GET"
    elif operation == "get_conversation":
        url = f"{base_url}/conversations/{conversation_id}"
        method = "GET"
    elif operation == "send_message":
        url = f"{base_url}/channels/CHANNEL_ID/messages"
        method = "POST"
    elif operation == "list_teammates":
        url = f"{base_url}/teammates"
        method = "GET"
    elif operation == "get_teammate":
        url = f"{base_url}/teammates/{conversation_id}"  # reusing for teammate_id
        method = "GET"
    else:
        url = base_url
        method = "GET"

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "bearer",
    }
    if payload:
        preview["payload"] = payload

    return preview


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

    normalized_operation = operation.lower()
    valid_operations = {
        "list_conversations",
        "get_conversation",
        "send_message",
        "list_teammates",
        "get_teammate",
    }
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    # Validation for specific operations
    if normalized_operation == "get_conversation":
        if not conversation_id:
            return validation_error("Missing required conversation_id", field="conversation_id")

    if normalized_operation == "send_message":
        if not channel_id:
            return validation_error("Missing required channel_id", field="channel_id")
        if not to:
            return validation_error("Missing required to (list of emails)", field="to")
        if not body:
            return validation_error("Missing required body", field="body")

    if normalized_operation == "get_teammate":
        if not teammate_id:
            return validation_error("Missing required teammate_id", field="teammate_id")

    headers = {
        "Authorization": f"Bearer {FRONT_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = "https://api2.frontapp.com"
    payload: Optional[Dict[str, Any]] = None

    # Build URL and payload based on operation
    if normalized_operation == "list_conversations":
        url = f"{base_url}/conversations"
        method = "GET"
    elif normalized_operation == "get_conversation":
        url = f"{base_url}/conversations/{conversation_id}"
        method = "GET"
    elif normalized_operation == "send_message":
        url = f"{base_url}/channels/{channel_id}/messages"
        method = "POST"
        payload = {
            "to": to,
            "body": body,
        }
        if subject:
            payload["subject"] = subject
    elif normalized_operation == "list_teammates":
        url = f"{base_url}/teammates"
        method = "GET"
    elif normalized_operation == "get_teammate":
        url = f"{base_url}/teammates/{teammate_id}"
        method = "GET"
    else:
        url = base_url
        method = "GET"

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            conversation_id=conversation_id or teammate_id,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Front request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        message = data.get("message") or data.get("_error") or "Front API error"
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
