# ruff: noqa: F821, F706
"""Call the FreshBooks API for accounting and time tracking operations."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.freshbooks.com"
DOCUMENTATION_URL = "https://www.freshbooks.com/api/start"


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
    url = API_BASE_URL
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

    # Most FreshBooks endpoints require business_id in path
    if business_id:
        url = f"{API_BASE_URL}/accounting/account/{business_id}/{endpoint}"
    else:
        url = f"{API_BASE_URL}/{endpoint}"

    if operation == "list":
        # List operation uses GET with optional query params
        url = f"{url}/{endpoint.rstrip('s')}"  # Some endpoints use singular form
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
        method = "POST"
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
        method = "PUT"
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
