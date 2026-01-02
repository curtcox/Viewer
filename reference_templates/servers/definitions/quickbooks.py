# ruff: noqa: F821, F706
"""Call the QuickBooks Online API for accounting operations."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
DOCUMENTATION_URL = "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account"


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
        QUICKBOOKS_REALM_ID: Company realm ID (from secrets, can be overridden by realm_id parameter)
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
        return error_response(
            "realm_id is required. Provide it via QUICKBOOKS_REALM_ID secret or realm_id parameter",
            error_type="validation_error",
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
                    "code": 'operation: "create"\nentity_type: "Customer"\ndata: \'{"DisplayName": "John Doe"}\'',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = ["query", "get", "create", "update", "delete"]
    if operation not in valid_operations:
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}",
            error_type="validation_error",
        )

    # Build request based on operation
    method = "GET"
    url = f"{API_BASE_URL}/{effective_realm_id}"
    payload = None
    params = {"minorversion": minor_version}

    if operation == "query":
        if not query:
            return error_response(
                "query is required for query operation",
                error_type="validation_error",
            )
        url = f"{url}/query"
        params["query"] = query
    elif operation == "get":
        if not entity_type or not entity_id:
            return error_response(
                "entity_type and entity_id are required for get operation",
                error_type="validation_error",
            )
        url = f"{url}/{entity_type.lower()}/{entity_id}"
    elif operation == "create":
        if not entity_type or not data:
            return error_response(
                "entity_type and data are required for create operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/{entity_type.lower()}"
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "update":
        if not entity_type or not data:
            return error_response(
                "entity_type and data are required for update operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/{entity_type.lower()}"
        params["operation"] = "update"
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "delete":
        if not entity_type or not entity_id:
            return error_response(
                "entity_type and entity_id are required for delete operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/{entity_type.lower()}"
        params["operation"] = "delete"
        payload = {"Id": entity_id, "SyncToken": "0"}  # SyncToken required for delete

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

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {QUICKBOOKS_ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    if method == "POST":
        headers["Content-Type"] = "application/json"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            params=params,
            timeout=timeout,
        )

        # Try to parse JSON response
        try:
            return {"output": response.json()}
        except Exception:
            # If JSON parsing fails, return raw content
            return error_response(
                f"Failed to parse response as JSON. Status: {response.status_code}",
                error_type="api_error",
                status_code=response.status_code,
                details={"raw_response": response.text[:500]},
            )

    except Exception as e:
        status_code = None
        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
        return error_response(
            f"API request failed: {str(e)}",
            error_type="api_error",
            status_code=status_code,
        )
