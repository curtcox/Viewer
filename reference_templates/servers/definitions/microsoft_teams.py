# ruff: noqa: F821, F706
"""Interact with Microsoft Teams API via Microsoft Graph."""

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
    "list_teams",
    "get_team",
    "list_channels",
    "send_message",
    "list_messages",
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
    operation: str = "list_teams",
    team_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    message: Optional[str] = None,
    top: int = 10,
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
    """Interact with Microsoft Teams API.

    Args:
        operation: Operation to perform (list_teams, get_team, list_channels, send_message, list_messages).
        team_id: Team ID (required for get_team, list_channels, send_message, list_messages).
        channel_id: Channel ID (required for send_message, list_messages).
        message: Message content for send_message.
        top: Maximum number of items to return (default: 10).
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
    if operation in ("get_team", "list_channels", "send_message", "list_messages") and not team_id:
        return validation_error(f"operation={operation} requires team_id")

    if operation in ("send_message", "list_messages") and not channel_id:
        return validation_error(f"operation={operation} requires channel_id")

    if operation == "send_message" and not message:
        return validation_error("send_message requires message")

    # Get authentication
    auth_manager_instance = auth_manager or _DEFAULT_AUTH_MANAGER
    client_instance = client or _DEFAULT_CLIENT

    # Determine auth method
    if MICROSOFT_ACCESS_TOKEN:
        headers = {"Authorization": f"Bearer {MICROSOFT_ACCESS_TOKEN}"}
    elif MICROSOFT_TENANT_ID and MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET:
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
    if operation == "list_teams":
        url = f"{_GRAPH_API_BASE}/me/joinedTeams"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "get_team":
        url = f"{_GRAPH_API_BASE}/teams/{team_id}"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "list_channels":
        url = f"{_GRAPH_API_BASE}/teams/{team_id}/channels"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "send_message":
        url = f"{_GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages"
        payload = {
            "body": {
                "content": message,
            }
        }
        params = {}
        method = "POST"
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "list_messages":
        url = f"{_GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages"
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

    result = _parse_json_response(response)
    if "output" in result:
        return result

    return {"output": result, "content_type": "application/json"}
