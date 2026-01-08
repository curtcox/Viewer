# ruff: noqa: F821, F706
"""Interact with Calendly to manage scheduling and event types."""

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
_BASE_URL = "https://api.calendly.com"

_OPERATIONS = {
    "get_user": OperationDefinition(),
    "list_event_types": OperationDefinition(required=(RequiredField("user_uri"),)),
    "get_event_type": OperationDefinition(required=(RequiredField("event_type_uuid"),)),
    "list_events": OperationDefinition(required=(RequiredField("user_uri"),)),
    "get_event": OperationDefinition(required=(RequiredField("event_uuid"),)),
    "list_invitees": OperationDefinition(required=(RequiredField("event_uuid"),)),
    "get_invitee": OperationDefinition(required=(RequiredField("invitee_uuid"),)),
    "cancel_event": OperationDefinition(
        required=(RequiredField("event_uuid"),),
        payload_builder=lambda **_: {"reason": "Cancelled via API"},
    ),
}

_ENDPOINT_BUILDERS = {
    "get_user": lambda base_url, **_: f"{base_url}/users/me",
    "list_event_types": lambda base_url, **_: f"{base_url}/event_types",
    "get_event_type": lambda base_url, event_type_uuid, **_: (
        f"{base_url}/event_types/{event_type_uuid}"
    ),
    "list_events": lambda base_url, **_: f"{base_url}/scheduled_events",
    "get_event": lambda base_url, event_uuid, **_: (
        f"{base_url}/scheduled_events/{event_uuid}"
    ),
    "list_invitees": lambda base_url, event_uuid, **_: (
        f"{base_url}/scheduled_events/{event_uuid}/invitees"
    ),
    "get_invitee": lambda base_url, invitee_uuid, **_: (
        f"{base_url}/scheduled_events/invitees/{invitee_uuid}"
    ),
    "cancel_event": lambda base_url, event_uuid, **_: (
        f"{base_url}/scheduled_events/{event_uuid}/cancellation"
    ),
}

_METHODS = {
    "cancel_event": "POST",
}


def _build_params(
    operation: str,
    *,
    user_uri: Optional[str],
    event_uuid: Optional[str],
    count: int,
) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if operation in {"list_event_types", "list_events"}:
        params["user"] = user_uri
        params["count"] = count
    elif operation == "list_invitees":
        params["count"] = count
    return params or None


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "bearer",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _calendly_error_message(response: object, data: object) -> str:
    status = getattr(response, "status_code", None)
    if status == 401:
        return "Invalid or missing CALENDLY_API_KEY"
    if status == 403:
        return "Insufficient permissions for this operation"

    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "Calendly API error"
    return "Calendly API error"


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

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        user_uri=user_uri,
        event_type_uuid=event_type_uuid,
        event_uuid=event_uuid,
        invitee_uuid=invitee_uuid,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    method = _METHODS.get(operation, "GET")
    url = _ENDPOINT_BUILDERS[operation](
        base_url=_BASE_URL,
        user_uri=user_uri,
        event_type_uuid=event_type_uuid,
        event_uuid=event_uuid,
        invitee_uuid=invitee_uuid,
    )
    params = _build_params(
        operation,
        user_uri=user_uri,
        event_uuid=event_uuid,
        count=count,
    )
    payload = result

    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                url=url,
                method=method,
                payload=payload,
                params=params,
            )
        }

    headers = {
        "Authorization": f"Bearer {CALENDLY_API_KEY}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_calendly_error_message,
        request_error_message="Calendly request failed",
        empty_response_statuses=(201, 204),
        empty_response_output={"success": True},
    )
