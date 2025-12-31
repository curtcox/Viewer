# ruff: noqa: F821, F706
"""Interact with Mailchimp API to manage audiences, campaigns, and members."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_lists",
    "get_list",
    "add_member",
    "get_member",
    "list_campaigns",
    "get_campaign",
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

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = f"https://{datacenter}.api.mailchimp.com/3.0"
    method = "GET"
    payload = None

    if operation == "list_lists":
        url = f"{base_url}/lists?count={count}"
    elif operation == "get_list":
        if not list_id:
            return validation_error("list_id is required for get_list operation")
        url = f"{base_url}/lists/{list_id}"
    elif operation == "add_member":
        if not list_id or not email:
            return validation_error(
                "list_id and email are required for add_member operation"
            )
        url = f"{base_url}/lists/{list_id}/members"
        method = "POST"
        payload = {"email_address": email, "status": "subscribed"}
        if member_data:
            payload.update(member_data)
    elif operation == "get_member":
        if not list_id or not email:
            return validation_error(
                "list_id and email are required for get_member operation"
            )
        # Mailchimp uses MD5 hash of lowercase email as member ID
        import hashlib

        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
        url = f"{base_url}/lists/{list_id}/members/{subscriber_hash}"
    elif operation == "list_campaigns":
        url = f"{base_url}/campaigns?count={count}"
    elif operation == "get_campaign":
        if not campaign_id:
            return validation_error(
                "campaign_id is required for get_campaign operation"
            )
        url = f"{base_url}/campaigns/{campaign_id}"

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Mailchimp uses HTTP Basic Auth with 'anystring' as username and API key as password
    import base64

    auth_str = base64.b64encode(f"anystring:{MAILCHIMP_API_KEY}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_str}",
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
            "Mailchimp request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("detail", "Mailchimp API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
