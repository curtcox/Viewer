# ruff: noqa: F821, F706
"""Interact with Gmail API to list, read, and send email messages."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    error_output,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send")
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_messages",
    "get_message",
    "send_message",
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
        "auth": "google_service_account",
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
    user_id: str = "me",
    message_id: Optional[str] = None,
    query: Optional[str] = None,
    max_results: int = 10,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Gmail API.

    Args:
        operation: Operation to perform (list_messages, get_message, send_message).
        user_id: User's email address or 'me' for the authenticated user.
        message_id: Message ID (required for get_message).
        query: Search query for list_messages (e.g., 'is:unread').
        max_results: Maximum number of messages to return (default: 10).
        to: Recipient email address (required for send_message).
        subject: Email subject (required for send_message).
        body: Email body (required for send_message).
        GOOGLE_SERVICE_ACCOUNT_JSON: Google service account JSON string.
        GOOGLE_ACCESS_TOKEN: Google OAuth access token (alternative to service account).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        auth_manager: Optional custom auth manager (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT
    auth_mgr = auth_manager or _DEFAULT_AUTH_MANAGER

    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN:
        return error_output(
            "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN",
            status_code=401,
            details="Provide either a service account JSON or an access token.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = f"https://gmail.googleapis.com/gmail/v1/users/{user_id}"
    method = "GET"
    payload = None

    if operation == "list_messages":
        url = f"{base_url}/messages?maxResults={max_results}"
        if query:
            url += f"&q={query}"
    elif operation == "get_message":
        if not message_id:
            return validation_error("message_id is required for get_message operation")
        url = f"{base_url}/messages/{message_id}"
    elif operation == "send_message":
        if not to or not subject or not body:
            return validation_error(
                "to, subject, and body are required for send_message operation"
            )
        url = f"{base_url}/messages/send"
        method = "POST"
        
        # Create RFC 2822 formatted message
        message = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        encoded_message = base64.urlsafe_b64encode(message.encode()).decode()
        payload = {"raw": encoded_message}

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Get access token
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            return error_output(
                "Invalid GOOGLE_SERVICE_ACCOUNT_JSON format",
                status_code=400,
                details="Service account JSON must be valid JSON.",
            )

        token_response = auth_mgr.get_access_token(
            service_account_info=service_account_info,
            scopes=_SCOPES,
        )
        if "error" in token_response.get("output", {}):
            return token_response

        access_token = token_response["access_token"]
    else:
        access_token = GOOGLE_ACCESS_TOKEN

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Gmail request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", {}).get("message", "Gmail API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
