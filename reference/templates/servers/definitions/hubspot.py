# ruff: noqa: F821, F706
"""Interact with HubSpot CRM to manage contacts and companies."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_contacts",
    "get_contact",
    "create_contact",
    "list_companies",
    "get_company",
    "create_company",
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
    operation: str = "list_contacts",
    contact_id: Optional[str] = None,
    company_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    HUBSPOT_ACCESS_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with HubSpot CRM API.

    Args:
        operation: Operation to perform (list_contacts, get_contact, create_contact,
                   list_companies, get_company, create_company).
        contact_id: Contact ID (required for get_contact).
        company_id: Company ID (required for get_company).
        properties: Properties dict for creating contacts/companies.
        limit: Maximum number of results for list operations.
        HUBSPOT_ACCESS_TOKEN: HubSpot OAuth access token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not HUBSPOT_ACCESS_TOKEN:
        return error_output(
            "Missing HUBSPOT_ACCESS_TOKEN",
            status_code=401,
            details="Provide a valid OAuth access token.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.hubapi.com"
    url: Optional[str] = None
    method = "GET"
    payload = None

    if operation == "list_contacts":
        url = f"{base_url}/crm/v3/objects/contacts?limit={limit}"
    elif operation == "get_contact":
        if not contact_id:
            return validation_error("contact_id is required for get_contact operation")
        url = f"{base_url}/crm/v3/objects/contacts/{contact_id}"
    elif operation == "create_contact":
        if not properties:
            return validation_error(
                "properties are required for create_contact operation"
            )
        url = f"{base_url}/crm/v3/objects/contacts"
        method = "POST"
        payload = {"properties": properties}
    elif operation == "list_companies":
        url = f"{base_url}/crm/v3/objects/companies?limit={limit}"
    elif operation == "get_company":
        if not company_id:
            return validation_error("company_id is required for get_company operation")
        url = f"{base_url}/crm/v3/objects/companies/{company_id}"
    elif operation == "create_company":
        if not properties:
            return validation_error(
                "properties are required for create_company operation"
            )
        url = f"{base_url}/crm/v3/objects/companies"
        method = "POST"
        payload = {"properties": properties}

    if url is None:
        return error_output(f"Internal error: unhandled operation '{operation}'")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
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
            "HubSpot request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("message", "HubSpot API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
