# ruff: noqa: F821, F706
"""Interact with Close CRM to manage leads, contacts, and opportunities."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_leads",
    "get_lead",
    "create_lead",
    "update_lead",
    "list_contacts",
    "get_contact",
    "create_contact",
    "list_opportunities",
    "get_opportunity",
    "create_opportunity",
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
    operation: str = "list_leads",
    lead_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    CLOSE_API_KEY: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Close CRM API.

    Args:
        operation: Operation to perform (list_leads, get_lead, create_lead, update_lead,
                   list_contacts, get_contact, create_contact, list_opportunities,
                   get_opportunity, create_opportunity).
        lead_id: Lead ID (required for get_lead, update_lead).
        contact_id: Contact ID (required for get_contact).
        opportunity_id: Opportunity ID (required for get_opportunity).
        data: Data for creating or updating records.
        limit: Maximum number of results for list operations.
        CLOSE_API_KEY: Close CRM API key.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not CLOSE_API_KEY:
        return error_output(
            "Missing CLOSE_API_KEY",
            status_code=401,
            details="Provide a valid API key.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.close.com/api/v1"
    url: Optional[str] = None
    method = "GET"
    payload = None

    if operation == "list_leads":
        url = f"{base_url}/lead/?_limit={limit}"
    elif operation == "get_lead":
        if not lead_id:
            return validation_error("lead_id is required for get_lead operation")
        url = f"{base_url}/lead/{lead_id}"
    elif operation == "create_lead":
        if not data:
            return validation_error("data is required for create_lead operation")
        url = f"{base_url}/lead/"
        method = "POST"
        payload = data
    elif operation == "update_lead":
        if not lead_id or not data:
            return validation_error(
                "lead_id and data are required for update_lead operation"
            )
        url = f"{base_url}/lead/{lead_id}"
        method = "PUT"
        payload = data
    elif operation == "list_contacts":
        url = f"{base_url}/contact/?_limit={limit}"
    elif operation == "get_contact":
        if not contact_id:
            return validation_error("contact_id is required for get_contact operation")
        url = f"{base_url}/contact/{contact_id}"
    elif operation == "create_contact":
        if not data:
            return validation_error("data is required for create_contact operation")
        url = f"{base_url}/contact/"
        method = "POST"
        payload = data
    elif operation == "list_opportunities":
        url = f"{base_url}/opportunity/?_limit={limit}"
    elif operation == "get_opportunity":
        if not opportunity_id:
            return validation_error(
                "opportunity_id is required for get_opportunity operation"
            )
        url = f"{base_url}/opportunity/{opportunity_id}"
    elif operation == "create_opportunity":
        if not data:
            return validation_error(
                "data is required for create_opportunity operation"
            )
        url = f"{base_url}/opportunity/"
        method = "POST"
        payload = data

    if url is None:
        return error_output(f"Internal error: unhandled operation '{operation}'")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout,
            auth=(CLOSE_API_KEY, ""),  # Basic auth with API key as username, empty password
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Close CRM request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", "Close CRM API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
