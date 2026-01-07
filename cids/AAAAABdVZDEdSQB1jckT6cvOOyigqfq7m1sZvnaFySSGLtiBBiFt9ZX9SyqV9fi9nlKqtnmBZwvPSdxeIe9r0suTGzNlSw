# ruff: noqa: F821, F706
"""Interact with Zoho CRM to manage accounts, contacts, leads, and deals."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_records",
    "get_record",
    "create_record",
    "update_record",
    "delete_record",
    "search_records",
}


_SUPPORTED_MODULES = {
    "Accounts",
    "Contacts",
    "Leads",
    "Deals",
    "Tasks",
    "Calls",
    "Meetings",
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
    operation: str = "list_records",
    module: str = "Accounts",
    record_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    criteria: Optional[str] = None,
    page: int = 1,
    per_page: int = 200,
    ZOHO_ACCESS_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Zoho CRM API.

    Args:
        operation: Operation to perform (list_records, get_record, create_record,
                   update_record, delete_record, search_records).
        module: Zoho CRM module (Accounts, Contacts, Leads, Deals, etc.).
        record_id: Record ID (required for get_record, update_record, delete_record).
        data: Data for creating or updating records.
        criteria: Search criteria for search_records (e.g., "(Email:equals:john@example.com)").
        page: Page number for pagination.
        per_page: Number of records per page (max 200).
        ZOHO_ACCESS_TOKEN: Zoho OAuth access token.
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not ZOHO_ACCESS_TOKEN:
        return error_output(
            "Missing ZOHO_ACCESS_TOKEN",
            status_code=401,
            details="Provide a valid OAuth access token.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    if module not in _SUPPORTED_MODULES:
        return validation_error(
            f"Invalid module: {module}. Valid modules: {', '.join(_SUPPORTED_MODULES)}"
        )

    # Build URL and method based on operation
    base_url = "https://www.zohoapis.com/crm/v3"
    url: Optional[str] = None
    method = "GET"
    payload = None

    if operation == "list_records":
        url = f"{base_url}/{module}?page={page}&per_page={per_page}"
    elif operation == "get_record":
        if not record_id:
            return validation_error("record_id is required for get_record operation")
        url = f"{base_url}/{module}/{record_id}"
    elif operation == "create_record":
        if not data:
            return validation_error("data is required for create_record operation")
        url = f"{base_url}/{module}"
        method = "POST"
        payload = {"data": [data]}
    elif operation == "update_record":
        if not record_id or not data:
            return validation_error(
                "record_id and data are required for update_record operation"
            )
        url = f"{base_url}/{module}/{record_id}"
        method = "PUT"
        payload = {"data": [data]}
    elif operation == "delete_record":
        if not record_id:
            return validation_error("record_id is required for delete_record operation")
        url = f"{base_url}/{module}/{record_id}"
        method = "DELETE"
    elif operation == "search_records":
        if not criteria:
            return validation_error("criteria is required for search_records operation")
        url = f"{base_url}/{module}/search?criteria={criteria}&page={page}&per_page={per_page}"

    if url is None:
        return error_output(f"Internal error: unhandled operation '{operation}'")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Authorization": f"Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}",
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
            "Zoho CRM request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("message", "Zoho CRM API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
