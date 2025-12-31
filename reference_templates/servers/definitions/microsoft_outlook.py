# ruff: noqa: F821, F706
"""Interact with Microsoft Outlook Mail API via Microsoft Graph."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    error_output,
    validation_error,
)


_GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_messages",
    "get_message",
    "send_message",
    "delete_message",
    "list_folders",
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
        "auth": "microsoft_oauth",
    }

    if payload:
        preview["payload"] = payload

    return preview


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )


def main(
    *,
    operation: str = "list_messages",
    message_id: Optional[str] = None,
    folder: str = "inbox",
    top: int = 10,
    filter: Optional[str] = None,
    to_recipients: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    MICROSOFT_ACCESS_TOKEN: Optional[str] = None,
    MICROSOFT_TENANT_ID: Optional[str] = None,
    MICROSOFT_CLIENT_ID: Optional[str] = None,
    MICROSOFT_CLIENT_SECRET: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[MicrosoftAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Microsoft Outlook Mail API.

    Args:
        operation: Operation to perform (list_messages, get_message, send_message, delete_message, list_folders).
        message_id: Message ID (required for get_message, delete_message).
        folder: Folder to list messages from (default: inbox).
        top: Maximum number of messages to return (default: 10).
        filter: OData filter expression for list_messages.
        to_recipients: Comma-separated email addresses for send_message.
        subject: Email subject for send_message.
        body: Email body for send_message.
        MICROSOFT_ACCESS_TOKEN: Microsoft OAuth access token.
        MICROSOFT_TENANT_ID: Microsoft tenant ID (for client credentials flow).
        MICROSOFT_CLIENT_ID: Microsoft client ID (for client credentials flow).
        MICROSOFT_CLIENT_SECRET: Microsoft client secret (for client credentials flow).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional ExternalApiClient for testing.
        auth_manager: Optional MicrosoftAuthManager for testing.
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or error.
    """
    # Validate operation
    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Supported: {', '.join(sorted(_SUPPORTED_OPERATIONS))}"
        )

    # Validate operation-specific requirements
    if operation in ("get_message", "delete_message") and not message_id:
        return validation_error(f"operation={operation} requires message_id")

    if operation == "send_message":
        if not to_recipients:
            return validation_error("send_message requires to_recipients")
        if not subject:
            return validation_error("send_message requires subject")
        if not body:
            return validation_error("send_message requires body")

    # Get authentication
    auth_manager_instance = auth_manager or _DEFAULT_AUTH_MANAGER
    client_instance = client or _DEFAULT_CLIENT

    # Determine auth method
    if MICROSOFT_ACCESS_TOKEN:
        headers = {"Authorization": f"Bearer {MICROSOFT_ACCESS_TOKEN}"}
    elif MICROSOFT_TENANT_ID and MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET:
        # Use client credentials flow
        auth_result = auth_manager_instance.get_authorization(
            tenant_id=MICROSOFT_TENANT_ID,
            client_id=MICROSOFT_CLIENT_ID,
            client_secret=MICROSOFT_CLIENT_SECRET,
            scopes=["https://graph.microsoft.com/.default"],
        )
        if "output" in auth_result:
            return auth_result
        headers = auth_result["headers"]
    else:
        return error_output(
            "Authentication required",
            details="Provide MICROSOFT_ACCESS_TOKEN or all of MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET",
        )

    # Build request based on operation
    if operation == "list_messages":
        url = f"{_GRAPH_API_BASE}/me/mailFolders/{folder}/messages"
        params = {"$top": top}
        if filter:
            params["$filter"] = filter
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "get_message":
        url = f"{_GRAPH_API_BASE}/me/messages/{message_id}"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "send_message":
        url = f"{_GRAPH_API_BASE}/me/sendMail"
        to_list = [{"emailAddress": {"address": addr.strip()}} for addr in to_recipients.split(",")]
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": to_list,
            }
        }
        params = {}
        method = "POST"
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "delete_message":
        url = f"{_GRAPH_API_BASE}/me/messages/{message_id}"
        params = {}
        method = "DELETE"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "list_folders":
        url = f"{_GRAPH_API_BASE}/me/mailFolders"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    # Execute request
    headers["Content-Type"] = "application/json"

    try:
        if method == "GET":
            response = client_instance.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            response = client_instance.post(url, headers=headers, json=payload, timeout=timeout)
        elif method == "DELETE":
            response = client_instance.delete(url, headers=headers, timeout=timeout)
        else:
            return error_output(f"Unsupported HTTP method: {method}")
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            f"Request failed: {exc}",
            status_code=status,
            details=str(exc),
        )

    if not response.ok:
        error_details = _parse_json_response(response)
        return error_output(
            f"API request failed: {response.status_code}",
            status_code=response.status_code,
            details=error_details,
        )

    # DELETE returns 204 with no content
    if response.status_code == 204:
        return {"output": {"success": True, "message": "Resource deleted"}, "content_type": "application/json"}

    result = _parse_json_response(response)
    if "output" in result:
        return result

    return {"output": result, "content_type": "application/json"}
