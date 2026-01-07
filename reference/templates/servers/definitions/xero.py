# ruff: noqa: F821, F706
"""Call the Xero API for accounting operations."""

from __future__ import annotations

import json
from typing import Any, Optional

from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    error_output,
    error_response,
    execute_json_request,
    generate_form,
    missing_secret_error,
    validate_and_build_payload,
    validation_error,
    FormField,
)


API_BASE_URL = "https://api.xero.com/api.xro/2.0"
DOCUMENTATION_URL = "https://developer.xero.com/documentation/api/accounting/overview"


def _parse_json_or_error(value: str | dict, field_name: str) -> dict | tuple[str, str]:
    """Parse JSON string or return error tuple."""
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        return (f"Invalid JSON in {field_name} parameter: {str(e)}", field_name)


_OPERATIONS = {
    "list": OperationDefinition(
        required=(RequiredField("endpoint"),),
        payload_builder=lambda endpoint, params, **_: {
            "method": "GET",
            "url_path": endpoint,
            "entity_id": None,
            "payload": None,
            "params": params,
        },
    ),
    "get": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("entity_id")),
        payload_builder=lambda endpoint, entity_id, **_: {
            "method": "GET",
            "url_path": endpoint,
            "entity_id": entity_id,
            "payload": None,
            "params": None,
        },
    ),
    "create": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("data")),
        payload_builder=lambda endpoint, data, **_: {
            "method": "PUT",  # Xero uses PUT for create
            "url_path": endpoint,
            "entity_id": None,
            "payload": data,
            "params": None,
        },
    ),
    "update": OperationDefinition(
        required=(
            RequiredField("endpoint"),
            RequiredField("entity_id"),
            RequiredField("data"),
        ),
        payload_builder=lambda endpoint, entity_id, data, **_: {
            "method": "POST",
            "url_path": endpoint,
            "entity_id": entity_id,
            "payload": data,
            "params": None,
        },
    ),
    "delete": OperationDefinition(
        required=(RequiredField("endpoint"), RequiredField("entity_id")),
        payload_builder=lambda endpoint, entity_id, **_: {
            "method": "DELETE",
            "url_path": endpoint,
            "entity_id": entity_id,
            "payload": None,
            "params": None,
        },
    ),
}


def main(
    operation: str = "",
    tenant_id: str = "",
    endpoint: str = "",
    entity_id: str = "",
    data: str = "",
    params: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    XERO_ACCESS_TOKEN: str,
    XERO_TENANT_ID: str = "",
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Xero API.

    Args:
        operation: Operation to perform (list, get, create, update, delete)
        tenant_id: Xero tenant ID (can be provided via secret or parameter)
        endpoint: API endpoint (e.g., Invoices, Contacts, Accounts, Payments)
        entity_id: Entity ID for get/update/delete operations
        data: JSON data for create/update operations
        params: Query parameters as JSON string (e.g., '{"where": "Status==\\"ACTIVE\\""}')
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        XERO_ACCESS_TOKEN: OAuth access token for authentication (from secrets)
        XERO_TENANT_ID: Tenant ID (from secrets, can be overridden by tenant_id parameter)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not XERO_ACCESS_TOKEN:
        return missing_secret_error("XERO_ACCESS_TOKEN")

    # Use tenant_id parameter if provided, otherwise use secret
    effective_tenant_id = tenant_id or XERO_TENANT_ID
    if not effective_tenant_id:
        return error_response(
            "tenant_id is required. Provide it via XERO_TENANT_ID secret or tenant_id parameter",
            error_type="validation_error",
        )

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="xero",
            title="Xero API",
            description="Access Xero accounting data and operations.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=["list", "get", "create", "update", "delete"],
                    required=True,
                ),
                FormField(
                    name="tenant_id",
                    label="Tenant ID",
                    placeholder="abc-123-xyz",
                    help_text="Organization ID (optional if XERO_TENANT_ID secret is set)",
                ),
                FormField(
                    name="endpoint",
                    label="Endpoint",
                    placeholder="Invoices",
                    help_text="e.g., Invoices, Contacts, Accounts, Payments, BankTransactions",
                    required=True,
                ),
                FormField(
                    name="entity_id",
                    label="Entity ID",
                    placeholder="abc-123-xyz",
                    help_text="Required for get/update/delete operations",
                ),
                FormField(
                    name="data",
                    label="Data (JSON)",
                    field_type="textarea",
                    placeholder='{"Name": "John Doe", "EmailAddress": "john@example.com"}',
                    help_text="JSON data for create/update operations",
                ),
                FormField(
                    name="params",
                    label="Query Parameters (JSON)",
                    field_type="textarea",
                    placeholder='{"where": "Status==\\"ACTIVE\\"", "order": "Name ASC"}',
                    help_text="Optional query parameters for list operations",
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
                    "code": 'operation: "list"\nendpoint: "Invoices"',
                },
                {
                    "title": "Get contact",
                    "code": 'operation: "get"\nendpoint: "Contacts"\nentity_id: "abc-123-xyz"',
                },
                {
                    "title": "Create contact",
                    "code": (
                        'operation: "create"\nendpoint: "Contacts"\n'
                        'data: \'{"Name": "John Doe", "EmailAddress": "john@example.com"}\''
                    ),
                },
                {
                    "title": "Filter invoices",
                    "code": (
                        'operation: "list"\nendpoint: "Invoices"\n'
                        'params: \'{"where": "Status==\\\\"AUTHORISED\\\\""}\''
                    ),
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    if operation not in _OPERATIONS:
        valid_ops = list(_OPERATIONS.keys())
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_ops)}",
            error_type="validation_error",
        )

    # Parse params if provided
    query_params = None
    if params:
        parsed = _parse_json_or_error(params, "params")
        if isinstance(parsed, tuple):
            return error_response(parsed[0], error_type="validation_error")
        query_params = parsed

    # Parse data if provided
    parsed_data = None
    if data:
        parsed = _parse_json_or_error(data, "data")
        if isinstance(parsed, tuple):
            return error_response(parsed[0], error_type="validation_error")
        parsed_data = parsed

    # Validate and build request configuration
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        endpoint=endpoint,
        entity_id=entity_id,
        data=parsed_data,
        params=query_params,
    )
    if isinstance(result, tuple):
        return error_response(result[0], error_type="validation_error")

    # Extract request configuration
    method = result["method"]
    url_path = result["url_path"]
    entity_id_part = result["entity_id"]
    payload = result["payload"]
    params_dict = result["params"]

    # Build URL
    url = f"{API_BASE_URL}/{url_path}"
    if entity_id_part:
        url = f"{url}/{entity_id_part}"

    # Dry run: return preview
    if dry_run:
        preview: dict[str, Any] = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {
                "Authorization": "Bearer [REDACTED]",
                "Xero-tenant-id": "[REDACTED]",
            },
        }
        if params_dict:
            preview["params"] = params_dict
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    # Build headers
    headers = {
        "Authorization": f"Bearer {XERO_ACCESS_TOKEN}",
        "Xero-tenant-id": effective_tenant_id,
        "Accept": "application/json",
    }
    if method in ["PUT", "POST"]:
        headers["Content-Type"] = "application/json"

    # Execute request
    return execute_json_request(
        client,
        method,
        url,
        headers=headers,
        json=payload,
        params=params_dict,
        timeout=timeout,
    )
