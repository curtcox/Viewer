# ruff: noqa: F821, F706
"""Interact with Salesforce CRM to manage objects like accounts, contacts, and opportunities."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

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
    "query": OperationDefinition(
        required=(RequiredField("soql_query"),),
        payload_builder=lambda base_url, soql_query, **_: {
            "url": f"{base_url}/query?q={soql_query}",
            "method": "GET",
            "payload": None,
        },
    ),
    "get_record": OperationDefinition(
        required=(RequiredField("sobject_type"), RequiredField("record_id")),
        payload_builder=lambda base_url, sobject_type, record_id, **_: {
            "url": f"{base_url}/sobjects/{sobject_type}/{record_id}",
            "method": "GET",
            "payload": None,
        },
    ),
    "create_record": OperationDefinition(
        required=(RequiredField("sobject_type"), RequiredField("data")),
        payload_builder=lambda base_url, sobject_type, data, **_: {
            "url": f"{base_url}/sobjects/{sobject_type}",
            "method": "POST",
            "payload": data,
        },
    ),
    "update_record": OperationDefinition(
        required=(
            RequiredField("sobject_type"),
            RequiredField("record_id"),
            RequiredField("data"),
        ),
        payload_builder=lambda base_url, sobject_type, record_id, data, **_: {
            "url": f"{base_url}/sobjects/{sobject_type}/{record_id}",
            "method": "PATCH",
            "payload": data,
        },
    ),
    "delete_record": OperationDefinition(
        required=(RequiredField("sobject_type"), RequiredField("record_id")),
        payload_builder=lambda base_url, sobject_type, record_id, **_: {
            "url": f"{base_url}/sobjects/{sobject_type}/{record_id}",
            "method": "DELETE",
            "payload": None,
        },
    ),
    "describe_object": OperationDefinition(
        required=(RequiredField("sobject_type"),),
        payload_builder=lambda base_url, sobject_type, **_: {
            "url": f"{base_url}/sobjects/{sobject_type}/describe",
            "method": "GET",
            "payload": None,
        },
    ),
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


def _salesforce_error_message(_response: requests.Response, data: Any) -> str:
    error_msg = "Salesforce API error"
    if isinstance(data, list) and data:
        return data[0].get("message", error_msg)
    if isinstance(data, dict):
        return data.get("message", error_msg)
    return error_msg


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

    base_url = f"{SALESFORCE_INSTANCE_URL.rstrip('/')}/services/data/v59.0"
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        base_url=base_url,
        soql_query=soql_query,
        sobject_type=sobject_type,
        record_id=record_id,
        data=data,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    url = result["url"]
    method = result["method"]
    payload = result["payload"]

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    api_client = client or _DEFAULT_CLIENT

    headers = {
        "Authorization": f"Bearer {SALESFORCE_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_salesforce_error_message,
        request_error_message="Salesforce request failed",
        include_exception_in_message=False,
        empty_response_statuses=(204,),
        empty_response_output={"success": True},
    )
