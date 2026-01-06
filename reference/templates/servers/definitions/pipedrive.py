# ruff: noqa: F821, F706
"""Interact with Pipedrive CRM to manage deals, persons, and organizations."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_deals",
    "get_deal",
    "create_deal",
    "update_deal",
    "list_persons",
    "get_person",
    "create_person",
    "list_organizations",
    "get_organization",
    "create_organization",
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
        "auth": "api_token",
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
    operation: str = "list_deals",
    deal_id: Optional[int] = None,
    person_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    PIPEDRIVE_API_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Pipedrive CRM API.

    Args:
        operation: Operation to perform (list_deals, get_deal, create_deal, update_deal,
                   list_persons, get_person, create_person, list_organizations,
                   get_organization, create_organization).
        deal_id: Deal ID (required for get_deal, update_deal).
        person_id: Person ID (required for get_person).
        organization_id: Organization ID (required for get_organization).
        data: Data for creating or updating records.
        limit: Maximum number of results for list operations.
        PIPEDRIVE_API_TOKEN: Pipedrive API token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not PIPEDRIVE_API_TOKEN:
        return error_output(
            "Missing PIPEDRIVE_API_TOKEN",
            status_code=401,
            details="Provide a valid API token.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://api.pipedrive.com/v1"
    method = "GET"
    payload = None
    url = ""

    if operation == "list_deals":
        url = f"{base_url}/deals?limit={limit}"
    elif operation == "get_deal":
        if not deal_id:
            return validation_error("deal_id is required for get_deal operation")
        url = f"{base_url}/deals/{deal_id}"
    elif operation == "create_deal":
        if not data:
            return validation_error("data is required for create_deal operation")
        url = f"{base_url}/deals"
        method = "POST"
        payload = data
    elif operation == "update_deal":
        if not deal_id or not data:
            return validation_error(
                "deal_id and data are required for update_deal operation"
            )
        url = f"{base_url}/deals/{deal_id}"
        method = "PUT"
        payload = data
    elif operation == "list_persons":
        url = f"{base_url}/persons?limit={limit}"
    elif operation == "get_person":
        if not person_id:
            return validation_error("person_id is required for get_person operation")
        url = f"{base_url}/persons/{person_id}"
    elif operation == "create_person":
        if not data:
            return validation_error("data is required for create_person operation")
        url = f"{base_url}/persons"
        method = "POST"
        payload = data
    elif operation == "list_organizations":
        url = f"{base_url}/organizations?limit={limit}"
    elif operation == "get_organization":
        if not organization_id:
            return validation_error(
                "organization_id is required for get_organization operation"
            )
        url = f"{base_url}/organizations/{organization_id}"
    elif operation == "create_organization":
        if not data:
            return validation_error(
                "data is required for create_organization operation"
            )
        url = f"{base_url}/organizations"
        method = "POST"
        payload = data

    if not url:
        return validation_error("Unsupported operation", field="operation")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Add API token to URL
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}api_token={PIPEDRIVE_API_TOKEN}"

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
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Pipedrive request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", "Pipedrive API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
