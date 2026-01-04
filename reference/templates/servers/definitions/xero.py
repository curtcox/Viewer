# ruff: noqa: F821, F706
"""Call the Xero API for accounting operations."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.xero.com/api.xro/2.0"
DOCUMENTATION_URL = "https://developer.xero.com/documentation/api/accounting/overview"


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
    valid_operations = ["list", "get", "create", "update", "delete"]
    if operation not in valid_operations:
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}",
            error_type="validation_error",
        )

    # Validate endpoint is provided
    if not endpoint:
        return error_response(
            "endpoint is required for all operations",
            error_type="validation_error",
        )

    # Build request based on operation
    method = "GET"
    url = f"{API_BASE_URL}/{endpoint}"
    payload = None
    query_params = {}

    # Parse params if provided
    if params:
        try:
            import json
            query_params = json.loads(params) if isinstance(params, str) else params
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in params parameter: {str(e)}",
                error_type="validation_error",
            )

    if operation == "list":
        # List operation uses GET with optional query params
        pass
    elif operation == "get":
        if not entity_id:
            return error_response(
                "entity_id is required for get operation",
                error_type="validation_error",
            )
        url = f"{url}/{entity_id}"
    elif operation == "create":
        if not data:
            return error_response(
                "data is required for create operation",
                error_type="validation_error",
            )
        method = "PUT"  # Xero uses PUT for create
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "update":
        if not entity_id or not data:
            return error_response(
                "entity_id and data are required for update operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/{entity_id}"
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "delete":
        if not entity_id:
            return error_response(
                "entity_id is required for delete operation",
                error_type="validation_error",
            )
        method = "DELETE"
        url = f"{url}/{entity_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {
                "Authorization": "Bearer [REDACTED]",
                "Xero-tenant-id": "[REDACTED]",
            },
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
        "Authorization": f"Bearer {XERO_ACCESS_TOKEN}",
        "Xero-tenant-id": effective_tenant_id,
        "Accept": "application/json",
    }
    if method in ["PUT", "POST"]:
        headers["Content-Type"] = "application/json"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            params=query_params if query_params else None,
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
