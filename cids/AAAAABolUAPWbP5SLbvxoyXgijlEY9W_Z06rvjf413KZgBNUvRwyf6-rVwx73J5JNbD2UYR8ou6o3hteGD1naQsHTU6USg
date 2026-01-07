# ruff: noqa: F821, F706
"""Interact with Insightly CRM to manage contacts, organizations, and opportunities."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_contacts",
    "get_contact",
    "create_contact",
    "update_contact",
    "list_organizations",
    "get_organization",
    "create_organization",
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
    operation: str = "list_contacts",
    contact_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    opportunity_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
    top: int = 100,
    INSIGHTLY_API_KEY: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Insightly CRM API.

    Args:
        operation: Operation to perform (list_contacts, get_contact, create_contact,
                   update_contact, list_organizations, get_organization, create_organization,
                   list_opportunities, get_opportunity, create_opportunity).
        contact_id: Contact ID (required for get_contact, update_contact).
        organization_id: Organization ID (required for get_organization).
        opportunity_id: Opportunity ID (required for get_opportunity).
        data: Data for creating or updating records.
        top: Maximum number of results for list operations.
        INSIGHTLY_API_KEY: Insightly API key.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not INSIGHTLY_API_KEY:
        return error_output(
            "Missing INSIGHTLY_API_KEY",
            status_code=401,
            details="Provide a valid API key.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.insightly.com/v3.1"
    url: Optional[str] = None
    method = "GET"
    payload = None

    if operation == "list_contacts":
        url = f"{base_url}/Contacts?top={top}"
    elif operation == "get_contact":
        if not contact_id:
            return validation_error("contact_id is required for get_contact operation")
        url = f"{base_url}/Contacts/{contact_id}"
    elif operation == "create_contact":
        if not data:
            return validation_error("data is required for create_contact operation")
        url = f"{base_url}/Contacts"
        method = "POST"
        payload = data
    elif operation == "update_contact":
        if not contact_id or not data:
            return validation_error(
                "contact_id and data are required for update_contact operation"
            )
        url = f"{base_url}/Contacts"
        method = "PUT"
        payload = data
    elif operation == "list_organizations":
        url = f"{base_url}/Organisations?top={top}"
    elif operation == "get_organization":
        if not organization_id:
            return validation_error(
                "organization_id is required for get_organization operation"
            )
        url = f"{base_url}/Organisations/{organization_id}"
    elif operation == "create_organization":
        if not data:
            return validation_error(
                "data is required for create_organization operation"
            )
        url = f"{base_url}/Organisations"
        method = "POST"
        payload = data
    elif operation == "list_opportunities":
        url = f"{base_url}/Opportunities?top={top}"
    elif operation == "get_opportunity":
        if not opportunity_id:
            return validation_error(
                "opportunity_id is required for get_opportunity operation"
            )
        url = f"{base_url}/Opportunities/{opportunity_id}"
    elif operation == "create_opportunity":
        if not data:
            return validation_error(
                "data is required for create_opportunity operation"
            )
        url = f"{base_url}/Opportunities"
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
            auth=(INSIGHTLY_API_KEY, ""),  # Basic auth with API key as username, empty password
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Insightly request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if isinstance(parsed, dict) and "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", "Insightly API error") if isinstance(parsed, dict) else "Insightly API error",
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if isinstance(parsed, dict) and "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
