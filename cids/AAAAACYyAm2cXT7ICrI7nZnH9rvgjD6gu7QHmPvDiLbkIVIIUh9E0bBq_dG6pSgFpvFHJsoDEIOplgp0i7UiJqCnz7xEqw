# ruff: noqa: F821, F706
"""Call the QuickBooks Online API for accounting operations."""

import json
from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    missing_secret_error,
    generate_form,
    FormField,
    validate_and_build_payload,
    validation_error,
)


API_BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
DOCUMENTATION_URL = (
    "https://developer.intuit.com/app/developer/qbo/docs/api/"
    "accounting/all-entities/account"
)

_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "query": OperationDefinition(
        required=(RequiredField("query"),),
    ),
    "get": OperationDefinition(
        required=(RequiredField("entity_type"), RequiredField("entity_id")),
    ),
    "create": OperationDefinition(
        required=(RequiredField("entity_type"), RequiredField("data")),
        payload_builder=lambda data, **_: data,
    ),
    "update": OperationDefinition(
        required=(RequiredField("entity_type"), RequiredField("data")),
        payload_builder=lambda data, **_: data,
    ),
    "delete": OperationDefinition(
        required=(RequiredField("entity_type"), RequiredField("entity_id")),
        payload_builder=lambda entity_id, **_: {"Id": entity_id, "SyncToken": "0"},
    ),
}

_ENDPOINT_BUILDERS = {
    "query": lambda **_: "query",
    "get": lambda entity_type, entity_id, **_: f"{entity_type.lower()}/{entity_id}",
    "create": lambda entity_type, **_: entity_type.lower(),
    "update": lambda entity_type, **_: entity_type.lower(),
    "delete": lambda entity_type, **_: entity_type.lower(),
}

_METHODS = {
    "create": "POST",
    "update": "POST",
    "delete": "POST",
}


def _quickbooks_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        fault = data.get("Fault")
        if isinstance(fault, dict):
            errors = fault.get("Error")
            if isinstance(errors, list) and errors:
                first = errors[0]
                if isinstance(first, dict):
                    return (
                        first.get("Detail")
                        or first.get("Message")
                        or first.get("code")
                        or "QuickBooks API error"
                    )
                return str(first)
        return data.get("message") or "QuickBooks API error"
    return "QuickBooks API error"


def main(
    operation: str = "",
    realm_id: str = "",
    entity_type: str = "",
    entity_id: str = "",
    query: str = "",
    data: str = "",
    minor_version: str = "65",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    QUICKBOOKS_ACCESS_TOKEN: str,
    QUICKBOOKS_REALM_ID: str = "",
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the QuickBooks Online API.

    Args:
        operation: Operation to perform (query, get, create, update, delete)
        realm_id: Company realm ID (can be provided via secret or parameter)
        entity_type: Entity type (e.g., Account, Invoice, Customer, Payment)
        entity_id: Entity ID for get/update/delete operations
        query: SQL-like query for query operation (e.g., "SELECT * FROM Customer")
        data: JSON data for create/update operations
        minor_version: API minor version (default: 65)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        QUICKBOOKS_ACCESS_TOKEN: OAuth access token for authentication (from secrets)
        QUICKBOOKS_REALM_ID: Company realm ID (from secrets, can be overridden
                             by realm_id parameter)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not QUICKBOOKS_ACCESS_TOKEN:
        return missing_secret_error("QUICKBOOKS_ACCESS_TOKEN")

    # Use realm_id parameter if provided, otherwise use secret
    effective_realm_id = realm_id or QUICKBOOKS_REALM_ID
    if not effective_realm_id:
        return validation_error(
            "realm_id is required. Provide it via QUICKBOOKS_REALM_ID secret or realm_id parameter",
            field="realm_id",
        )

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="quickbooks",
            title="QuickBooks Online API",
            description="Access QuickBooks Online accounting data and operations.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=["query", "get", "create", "update", "delete"],
                    required=True,
                ),
                FormField(
                    name="realm_id",
                    label="Realm ID",
                    placeholder="123456789",
                    help_text="Company ID (optional if QUICKBOOKS_REALM_ID secret is set)",
                ),
                FormField(
                    name="entity_type",
                    label="Entity Type",
                    placeholder="Customer",
                    help_text="e.g., Account, Invoice, Customer, Payment, Vendor",
                ),
                FormField(
                    name="entity_id",
                    label="Entity ID",
                    placeholder="1",
                    help_text="Required for get/update/delete operations",
                ),
                FormField(
                    name="query",
                    label="Query",
                    field_type="textarea",
                    placeholder="SELECT * FROM Customer WHERE Active = true",
                    help_text="SQL-like query for query operation",
                ),
                FormField(
                    name="data",
                    label="Data (JSON)",
                    field_type="textarea",
                    placeholder='{"DisplayName": "John Doe"}',
                    help_text="JSON data for create/update operations",
                ),
                FormField(
                    name="minor_version",
                    label="Minor Version",
                    default="65",
                    help_text="API minor version",
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
                    "title": "Query customers",
                    "code": 'operation: "query"\nquery: "SELECT * FROM Customer"',
                },
                {
                    "title": "Get invoice",
                    "code": 'operation: "get"\nentity_type: "Invoice"\nentity_id: "123"',
                },
                {
                    "title": "Create customer",
                    "code": (
                        'operation: "create"\nentity_type: "Customer"\n'
                        'data: \'{"DisplayName": "John Doe"}\''
                    ),
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    parsed_data = None
    if data:
        try:
            parsed_data = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as exc:
            return validation_error(f"Invalid JSON in data parameter: {exc}", field="data")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        query=query,
        entity_type=entity_type,
        entity_id=entity_id,
        data=parsed_data,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    base_url = f"{API_BASE_URL}/{effective_realm_id}"
    endpoint = _ENDPOINT_BUILDERS[operation](
        entity_type=entity_type,
        entity_id=entity_id,
    )
    url = f"{base_url}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    params = {"minorversion": minor_version}
    if operation == "query":
        params["query"] = query
    if operation == "update":
        params["operation"] = "update"
    if operation == "delete":
        params["operation"] = "delete"
    payload = result if isinstance(result, dict) else None

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
            "params": params,
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    api_client = client or _DEFAULT_CLIENT

    headers = {
        "Authorization": f"Bearer {QUICKBOOKS_ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    if method == "POST":
        headers["Content-Type"] = "application/json"

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_quickbooks_error_message,
        request_error_message="QuickBooks request failed",
    )
