# ruff: noqa: F821, F706
"""Call the FreshBooks API for accounting and time tracking operations."""

from __future__ import annotations

import json
from typing import Any, Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    error_response,
    execute_json_request,
    missing_secret_error,
    generate_form,
    validate_and_build_payload,
    FormField,
)


API_BASE_URL = "https://api.freshbooks.com"
DOCUMENTATION_URL = "https://www.freshbooks.com/api/start"


def _parse_json_or_error(value: str | dict, field_name: str) -> dict[str, Any] | tuple[str, str]:
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        return (f"Invalid JSON in {field_name} parameter: {str(e)}", field_name)


def _build_base_url(endpoint: str, business_id: str) -> str:
    if business_id:
        return f"{API_BASE_URL}/accounting/account/{business_id}/{endpoint}"
    return f"{API_BASE_URL}/{endpoint}"


_OPERATIONS = {
    "list": OperationDefinition(
        required=(RequiredField("endpoint"),),
        payload_builder=lambda endpoint, business_id, params, **_: {
            "method": "GET",
            "url": f"{_build_base_url(endpoint, business_id)}/{endpoint.rstrip('s')}",
            "payload": None,
            "params": params,
        },
    ),
    "get": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("entity_id")),
        payload_builder=lambda endpoint, business_id, entity_id, **_: {
            "method": "GET",
            "url": f"{_build_base_url(endpoint, business_id)}/{entity_id}",
            "payload": None,
            "params": None,
        },
    ),
    "create": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("data")),
        payload_builder=lambda endpoint, business_id, data, **_: {
            "method": "POST",
            "url": _build_base_url(endpoint, business_id),
            "payload": data,
            "params": None,
        },
    ),
    "update": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("entity_id"), RequiredField("data")),
        payload_builder=lambda endpoint, business_id, entity_id, data, **_: {
            "method": "PUT",
            "url": f"{_build_base_url(endpoint, business_id)}/{entity_id}",
            "payload": data,
            "params": None,
        },
    ),
    "delete": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("entity_id")),
        payload_builder=lambda endpoint, business_id, entity_id, **_: {
            "method": "DELETE",
            "url": f"{_build_base_url(endpoint, business_id)}/{entity_id}",
            "payload": None,
            "params": None,
        },
    ),
}


def main(
    operation: str = "",
    endpoint: str = "",
    business_id: str = "",
    entity_id: str = "",
    data: str = "",
    params: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    FRESHBOOKS_ACCESS_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the FreshBooks API.

    Args:
        operation: Operation to perform (list, get, create, update, delete)
        endpoint: API endpoint (e.g., invoices, clients, expenses, time_entries)
        business_id: FreshBooks business/account ID (required for most operations)
        entity_id: Entity ID for get/update/delete operations
        data: JSON data for create/update operations
        params: Query parameters as JSON string (e.g., '{"include[]": "lines"}')
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        FRESHBOOKS_ACCESS_TOKEN: OAuth access token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not FRESHBOOKS_ACCESS_TOKEN:
        return missing_secret_error("FRESHBOOKS_ACCESS_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="freshbooks",
            title="FreshBooks API",
            description="Access FreshBooks accounting, invoicing, and time tracking data.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=["list", "get", "create", "update", "delete"],
                    required=True,
                ),
                FormField(
                    name="endpoint",
                    label="Endpoint",
                    placeholder="invoices",
                    help_text="e.g., invoices, clients, expenses, time_entries, payments",
                    required=True,
                ),
                FormField(
                    name="business_id",
                    label="Business ID",
                    placeholder="12345",
                    help_text="FreshBooks account ID (required for most endpoints)",
                ),
                FormField(
                    name="entity_id",
                    label="Entity ID",
                    placeholder="67890",
                    help_text="Required for get/update/delete operations",
                ),
                FormField(
                    name="data",
                    label="Data (JSON)",
                    field_type="textarea",
                    placeholder='{"organization": "Acme Corp", "email": "contact@example.com"}',
                    help_text="JSON data for create/update operations",
                ),
                FormField(
                    name="params",
                    label="Query Parameters (JSON)",
                    field_type="textarea",
                    placeholder='{"include[]": "lines"}',
                    help_text="Optional query parameters",
                ),
                FormField(name="timeout", label="Timeout (seconds)", default="60"),
                FormField(
                    name="dry_run",
                    label="Dry Run",
                    field_type="select",
                    options=["true", "false"],
                    default="true",
                    help_text="Preview the request without executing it",
                ),
            ],
            examples=[
                {
                    "title": "List invoices",
                    "code": 'operation: "list"\nendpoint: "invoices"\nbusiness_id: "12345"',
                },
                {
                    "title": "Get client",
                    "code": (
                        'operation: "get"\nendpoint: "clients"\n'
                        'business_id: "12345"\nentity_id: "67890"'
                    ),
                },
                {
                    "title": "Create client",
                    "code": (
                        'operation: "create"\nendpoint: "clients"\n'
                        'business_id: "12345"\ndata: \'{"organization": "Acme Corp"}\''
                    ),
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    query_params = None
    if params:
        parsed = _parse_json_or_error(params, "params")
        if isinstance(parsed, tuple):
            return error_response(parsed[0], error_type="validation_error")
        query_params = parsed

    payload_data = None
    if data:
        parsed = _parse_json_or_error(data, "data")
        if isinstance(parsed, tuple):
            return error_response(parsed[0], error_type="validation_error")
        payload_data = parsed

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        endpoint=endpoint,
        business_id=business_id,
        entity_id=entity_id,
        data=payload_data,
        params=query_params,
    )
    if isinstance(result, tuple):
        return error_response(result[0], error_type="validation_error")
    if result is None:
        return error_response("Unable to build request", error_type="validation_error")

    method = result["method"]
    url = result["url"]
    payload = result["payload"]
    query_params = result["params"]

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
        }
        if query_params:
            preview["params"] = query_params
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {FRESHBOOKS_ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    if method in ["POST", "PUT"]:
        headers["Content-Type"] = "application/json"

    return execute_json_request(
        client,
        method,
        url,
        headers=headers,
        params=query_params,
        json=payload,
        timeout=timeout,
        request_error_message="FreshBooks API request failed",
    )
