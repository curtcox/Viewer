# ruff: noqa: F821, F706
"""Interact with Zoom API to manage meetings and users."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_meetings",
    "get_meeting",
    "create_meeting",
    "list_users",
    "get_user",
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
    operation: str = "list_meetings",
    user_id: str = "me",
    meeting_id: Optional[str] = None,
    meeting_data: Optional[Dict[str, Any]] = None,
    page_size: int = 30,
    ZOOM_ACCESS_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Zoom API.

    Args:
        operation: Operation to perform (list_meetings, get_meeting, create_meeting,
                   list_users, get_user).
        user_id: User ID or 'me' for the authenticated user (default: 'me').
        meeting_id: Meeting ID (required for get_meeting).
        meeting_data: Meeting properties for create_meeting operation.
        page_size: Maximum number of results for list operations.
        ZOOM_ACCESS_TOKEN: Zoom OAuth access token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not ZOOM_ACCESS_TOKEN:
        return error_output(
            "Missing ZOOM_ACCESS_TOKEN",
            status_code=401,
            details="Provide a valid OAuth access token.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.zoom.us/v2"
    method = "GET"
    payload = None

    if operation == "list_meetings":
        url = f"{base_url}/users/{user_id}/meetings?page_size={page_size}"
    elif operation == "get_meeting":
        if not meeting_id:
            return validation_error("meeting_id is required for get_meeting operation")
        url = f"{base_url}/meetings/{meeting_id}"
    elif operation == "create_meeting":
        if not meeting_data:
            return validation_error(
                "meeting_data is required for create_meeting operation"
            )
        url = f"{base_url}/users/{user_id}/meetings"
        method = "POST"
        payload = meeting_data
    elif operation == "list_users":
        url = f"{base_url}/users?page_size={page_size}"
    elif operation == "get_user":
        url = f"{base_url}/users/{user_id}"

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Authorization": f"Bearer {ZOOM_ACCESS_TOKEN}",
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
            "Zoom request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("message", "Zoom API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
