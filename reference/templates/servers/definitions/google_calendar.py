# ruff: noqa: F821, F706
"""Interact with Google Calendar API to manage events."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    error_output,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/calendar",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_events",
    "get_event",
    "create_event",
    "update_event",
    "delete_event",
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
    operation: str = "list_events",
    calendar_id: str = "primary",
    event_id: Optional[str] = None,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    attendees: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Calendar API.

    Args:
        operation: Operation to perform (list_events, get_event, create_event, update_event, delete_event).
        calendar_id: Calendar ID (default: primary).
        event_id: Event ID (required for get_event, update_event, delete_event).
        max_results: Maximum number of events to return (default: 10).
        time_min: Lower bound for event start time (RFC3339 timestamp).
        time_max: Upper bound for event start time (RFC3339 timestamp).
        summary: Event title (required for create_event).
        description: Event description.
        start_time: Event start time (RFC3339 timestamp, required for create_event).
        end_time: Event end time (RFC3339 timestamp, required for create_event).
        attendees: Comma-separated list of attendee emails.
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
    base_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}"
    method = "GET"
    payload = None

    if operation == "list_events":
        url = f"{base_url}/events?maxResults={max_results}"
        if time_min:
            url += f"&timeMin={time_min}"
        if time_max:
            url += f"&timeMax={time_max}"
    elif operation == "get_event":
        if not event_id:
            return validation_error("event_id is required for get_event operation")
        url = f"{base_url}/events/{event_id}"
    elif operation == "create_event":
        if not summary or not start_time or not end_time:
            return validation_error(
                "summary, start_time, and end_time are required for create_event operation"
            )
        url = f"{base_url}/events"
        method = "POST"
        payload = {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }
        if description:
            payload["description"] = description
        if attendees:
            payload["attendees"] = [{"email": email.strip()} for email in attendees.split(",")]
    elif operation == "update_event":
        if not event_id:
            return validation_error("event_id is required for update_event operation")
        url = f"{base_url}/events/{event_id}"
        method = "PATCH"
        payload = {}
        if summary:
            payload["summary"] = summary
        if description:
            payload["description"] = description
        if start_time:
            payload["start"] = {"dateTime": start_time}
        if end_time:
            payload["end"] = {"dateTime": end_time}
    elif operation == "delete_event":
        if not event_id:
            return validation_error("event_id is required for delete_event operation")
        url = f"{base_url}/events/{event_id}"
        method = "DELETE"

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
            "Google Calendar request failed", status_code=status, details=str(exc)
        )

    if operation == "delete_event":
        # DELETE returns 204 No Content on success
        if response.status_code == 204:
            return {"output": {"message": "Event deleted successfully"}}

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", {}).get("message", "Google Calendar API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
