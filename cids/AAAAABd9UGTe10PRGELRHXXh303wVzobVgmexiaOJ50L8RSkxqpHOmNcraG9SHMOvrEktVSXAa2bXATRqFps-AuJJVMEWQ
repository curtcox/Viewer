# ruff: noqa: F821, F706
"""Interact with Zoho CRM to manage accounts, contacts, leads, and deals."""

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


_OPERATIONS = {
    "list_records": OperationDefinition(),
    "get_record": OperationDefinition(
        required=(RequiredField("record_id", "record_id is required for get_record operation"),),
    ),
    "create_record": OperationDefinition(
        required=(RequiredField("data", "data is required for create_record operation"),),
        payload_builder=lambda data, **_: {"data": [data]},
    ),
    "update_record": OperationDefinition(
        required=(
            RequiredField("record_id", "record_id is required for update_record operation"),
            RequiredField("data", "data is required for update_record operation"),
        ),
        payload_builder=lambda data, **_: {"data": [data]},
    ),
    "delete_record": OperationDefinition(
        required=(RequiredField("record_id", "record_id is required for delete_record operation"),),
    ),
    "search_records": OperationDefinition(
        required=(RequiredField("criteria", "criteria is required for search_records operation"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_records": lambda base_url, module, page, per_page, **_: (
        f"{base_url}/{module}?page={page}&per_page={per_page}"
    ),
    "get_record": lambda base_url, module, record_id, **_: f"{base_url}/{module}/{record_id}",
    "create_record": lambda base_url, module, **_: f"{base_url}/{module}",
    "update_record": lambda base_url, module, record_id, **_: f"{base_url}/{module}/{record_id}",
    "delete_record": lambda base_url, module, record_id, **_: f"{base_url}/{module}/{record_id}",
    "search_records": lambda base_url, module, criteria, page, per_page, **_: (
        f"{base_url}/{module}/search?criteria={criteria}&page={page}&per_page={per_page}"
    ),
}

_METHODS = {
    "create_record": "POST",
    "update_record": "PUT",
    "delete_record": "DELETE",
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


def _zoho_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "Zoho CRM API error"
    return "Zoho CRM API error"


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

    if operation not in _OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_OPERATIONS)}"
        )

    if module not in _SUPPORTED_MODULES:
        return validation_error(
            f"Invalid module: {module}. Valid modules: {', '.join(_SUPPORTED_MODULES)}"
        )

    base_url = "https://www.zohoapis.com/crm/v3"
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        record_id=record_id,
        data=data,
        criteria=criteria,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    url = _ENDPOINT_BUILDERS[operation](
        base_url=base_url,
        module=module,
        record_id=record_id,
        criteria=criteria,
        page=page,
        per_page=per_page,
    )
    method = _METHODS.get(operation, "GET")

    if dry_run:
        return {
            "output": _build_preview(operation=operation, url=url, method=method, payload=payload)
        }

    headers = {
        "Authorization": f"Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_zoho_error_message,
        request_error_message="Zoho CRM request failed",
    )
