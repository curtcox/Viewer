# ruff: noqa: F821, F706
"""Interact with Salesforce CRM to manage objects like accounts, contacts, and opportunities."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "query",
    "get_record",
    "create_record",
    "update_record",
    "delete_record",
    "describe_object",
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
    operation: str = "query",
    soql_query: Optional[str] = None,
    sobject_type: Optional[str] = None,
    record_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    SALESFORCE_ACCESS_TOKEN: str,
    SALESFORCE_INSTANCE_URL: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Salesforce CRM API.

    Args:
        operation: Operation to perform (query, get_record, create_record,
                   update_record, delete_record, describe_object).
        soql_query: SOQL query string (required for query operation).
        sobject_type: Salesforce object type (e.g., Account, Contact, Opportunity).
        record_id: Record ID (required for get_record, update_record, delete_record).
        data: Data for creating or updating records.
        SALESFORCE_ACCESS_TOKEN: Salesforce OAuth access token.
        SALESFORCE_INSTANCE_URL: Salesforce instance URL (e.g., https://na1.salesforce.com).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT

    if not SALESFORCE_ACCESS_TOKEN:
        return error_output(
            "Missing SALESFORCE_ACCESS_TOKEN",
            status_code=401,
            details="Provide a valid OAuth access token.",
        )

    if not SALESFORCE_INSTANCE_URL:
        return error_output(
            "Missing SALESFORCE_INSTANCE_URL",
            status_code=401,
            details="Provide your Salesforce instance URL.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = f"{SALESFORCE_INSTANCE_URL.rstrip('/')}/services/data/v59.0"
    method = "GET"
    payload = None

    if operation == "query":
        if not soql_query:
            return validation_error("soql_query is required for query operation")
        url = f"{base_url}/query?q={soql_query}"
    elif operation == "get_record":
        if not sobject_type or not record_id:
            return validation_error(
                "sobject_type and record_id are required for get_record operation"
            )
        url = f"{base_url}/sobjects/{sobject_type}/{record_id}"
    elif operation == "create_record":
        if not sobject_type or not data:
            return validation_error(
                "sobject_type and data are required for create_record operation"
            )
        url = f"{base_url}/sobjects/{sobject_type}"
        method = "POST"
        payload = data
    elif operation == "update_record":
        if not sobject_type or not record_id or not data:
            return validation_error(
                "sobject_type, record_id, and data are required for update_record operation"
            )
        url = f"{base_url}/sobjects/{sobject_type}/{record_id}"
        method = "PATCH"
        payload = data
    elif operation == "delete_record":
        if not sobject_type or not record_id:
            return validation_error(
                "sobject_type and record_id are required for delete_record operation"
            )
        url = f"{base_url}/sobjects/{sobject_type}/{record_id}"
        method = "DELETE"
    elif operation == "describe_object":
        if not sobject_type:
            return validation_error("sobject_type is required for describe_object operation")
        url = f"{base_url}/sobjects/{sobject_type}/describe"

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    headers = {
        "Authorization": f"Bearer {SALESFORCE_ACCESS_TOKEN}",
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
            "Salesforce request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if isinstance(parsed, dict) and "error" in parsed.get("output", {}):
            return parsed
        # Salesforce returns errors as a list
        error_msg = "Salesforce API error"
        if isinstance(parsed, list) and len(parsed) > 0:
            error_msg = parsed[0].get("message", error_msg)
        elif isinstance(parsed, dict):
            error_msg = parsed.get("message", error_msg)
        return error_output(
            error_msg,
            status_code=response.status_code,
            response=parsed,
        )

    # DELETE returns 204 with no content
    if response.status_code == 204:
        return {"output": {"success": True}}

    parsed = _parse_json_response(response)
    if isinstance(parsed, dict) and "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
