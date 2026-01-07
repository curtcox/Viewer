# ruff: noqa: F821, F706
"""Interact with Calendly to manage scheduling and event types."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "get_user",
    "list_event_types",
    "get_event_type",
    "list_events",
    "get_event",
    "list_invitees",
    "get_invitee",
    "cancel_event",
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
    operation: str = "get_user",
    user_uri: Optional[str] = None,
    event_type_uuid: Optional[str] = None,
    event_uuid: Optional[str] = None,
    invitee_uuid: Optional[str] = None,
    count: int = 20,
    CALENDLY_API_KEY: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Calendly API.

    Args:
        operation: Operation to perform (get_user, list_event_types, get_event_type,
                   list_events, get_event, list_invitees, get_invitee, cancel_event).
        user_uri: User URI (required for list_event_types, list_events).
        event_type_uuid: Event type UUID (required for get_event_type).
        event_uuid: Event UUID (required for get_event, list_invitees, cancel_event).
        invitee_uuid: Invitee UUID (required for get_invitee).
        count: Maximum number of results for list operations.
        CALENDLY_API_KEY: Calendly API key (OAuth token).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not CALENDLY_API_KEY:
        return error_output(
            "Missing CALENDLY_API_KEY",
            status_code=401,
            details="Provide a valid API key (OAuth token).",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.calendly.com"
    method = "GET"
    payload = None
    url = ""

    if operation == "get_user":
        url = f"{base_url}/users/me"
    elif operation == "list_event_types":
        if not user_uri:
            return validation_error("user_uri is required for list_event_types operation")
        url = f"{base_url}/event_types?user={user_uri}&count={count}"
    elif operation == "get_event_type":
        if not event_type_uuid:
            return validation_error(
                "event_type_uuid is required for get_event_type operation"
            )
        url = f"{base_url}/event_types/{event_type_uuid}"
    elif operation == "list_events":
        if not user_uri:
            return validation_error("user_uri is required for list_events operation")
        url = f"{base_url}/scheduled_events?user={user_uri}&count={count}"
    elif operation == "get_event":
        if not event_uuid:
            return validation_error("event_uuid is required for get_event operation")
        url = f"{base_url}/scheduled_events/{event_uuid}"
    elif operation == "list_invitees":
        if not event_uuid:
            return validation_error("event_uuid is required for list_invitees operation")
        url = f"{base_url}/scheduled_events/{event_uuid}/invitees?count={count}"
    elif operation == "get_invitee":
        if not invitee_uuid:
            return validation_error("invitee_uuid is required for get_invitee operation")
        url = f"{base_url}/scheduled_events/invitees/{invitee_uuid}"
    elif operation == "cancel_event":
        if not event_uuid:
            return validation_error("event_uuid is required for cancel_event operation")
        url = f"{base_url}/scheduled_events/{event_uuid}/cancellation"
        method = "POST"
        payload = {"reason": "Cancelled via API"}

    if not url:
        return validation_error("Unsupported operation", field="operation")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Authorization": f"Bearer {CALENDLY_API_KEY}",
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
            "Calendly request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("message", "Calendly API error"),
            status_code=response.status_code,
            response=parsed,
        )

    # Some operations return 201 or 204
    if response.status_code in (201, 204):
        return {"output": {"success": True}}

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
