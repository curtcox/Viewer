# ruff: noqa: F821, F706
"""Interact with Mailchimp API to manage audiences, campaigns, and members."""

from __future__ import annotations

import base64
import hashlib
import re
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
    "list_lists": OperationDefinition(),
    "get_list": OperationDefinition(
        required=(RequiredField("list_id", "list_id is required for get_list operation"),),
    ),
    "add_member": OperationDefinition(
        required=(
            RequiredField("list_id", "list_id and email are required for add_member operation"),
            RequiredField("email", "list_id and email are required for add_member operation"),
        ),
        payload_builder=lambda email, member_data, **_: {
            "email_address": email,
            "status": "subscribed",
            **(member_data or {}),
        },
    ),
    "get_member": OperationDefinition(
        required=(
            RequiredField("list_id", "list_id and email are required for get_member operation"),
            RequiredField("email", "list_id and email are required for get_member operation"),
        ),
    ),
    "list_campaigns": OperationDefinition(),
    "get_campaign": OperationDefinition(
        required=(
            RequiredField("campaign_id", "campaign_id is required for get_campaign operation"),
        ),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_lists": lambda base_url, count, **_: f"{base_url}/lists?count={count}",
    "get_list": lambda base_url, list_id, **_: f"{base_url}/lists/{list_id}",
    "add_member": lambda base_url, list_id, **_: f"{base_url}/lists/{list_id}/members",
    "get_member": lambda base_url, list_id, email, **_: (
        f"{base_url}/lists/{list_id}/members/{_subscriber_hash(email)}"
    ),
    "list_campaigns": lambda base_url, count, **_: f"{base_url}/campaigns?count={count}",
    "get_campaign": lambda base_url, campaign_id, **_: f"{base_url}/campaigns/{campaign_id}",
}

_METHODS = {
    "add_member": "POST",
}


def _extract_datacenter(api_key: str) -> Optional[str]:
    """Extract datacenter from Mailchimp API key (format: key-dc)."""
    match = re.search(r"-([a-z0-9]+)$", api_key)
    return match.group(1) if match else None


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
        "auth": "basic",
    }

    if payload:
        preview["payload"] = payload

    return preview


def _mailchimp_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        return (
            data.get("detail")
            or data.get("title")
            or data.get("error")
            or "Mailchimp API error"
        )
    return "Mailchimp API error"


def _subscriber_hash(email: str) -> str:
    return hashlib.md5(email.lower().encode()).hexdigest()


def main(
    *,
    operation: str = "list_lists",
    list_id: Optional[str] = None,
    email: Optional[str] = None,
    member_data: Optional[Dict[str, Any]] = None,
    campaign_id: Optional[str] = None,
    count: int = 100,
    MAILCHIMP_API_KEY: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Mailchimp API.

    Args:
        operation: Operation to perform (list_lists, get_list, add_member,
                   get_member, list_campaigns, get_campaign).
        list_id: List/Audience ID (required for list-specific operations).
        email: Member email (required for member operations).
        member_data: Member properties for add_member operation.
        campaign_id: Campaign ID (required for get_campaign).
        count: Maximum number of results for list operations.
        MAILCHIMP_API_KEY: Mailchimp API key (format: key-datacenter).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not MAILCHIMP_API_KEY:
        return error_output(
            "Missing MAILCHIMP_API_KEY",
            status_code=401,
            details="Provide a valid Mailchimp API key.",
        )

    # Extract datacenter from API key
    datacenter = _extract_datacenter(MAILCHIMP_API_KEY)
    if not datacenter:
        return error_output(
            "Invalid MAILCHIMP_API_KEY format",
            status_code=401,
            details="API key must be in format: key-datacenter (e.g., key-us1)",
        )

    if operation not in _OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_OPERATIONS)}"
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        list_id=list_id,
        email=email,
        member_data=member_data,
        campaign_id=campaign_id,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    base_url = f"https://{datacenter}.api.mailchimp.com/3.0"
    url = _ENDPOINT_BUILDERS[operation](
        base_url=base_url,
        list_id=list_id,
        email=email,
        campaign_id=campaign_id,
        count=count,
    )
    method = _METHODS.get(operation, "GET")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    auth_str = base64.b64encode(f"anystring:{MAILCHIMP_API_KEY}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_str}",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_mailchimp_error_message,
        request_error_message="Mailchimp request failed",
    )
