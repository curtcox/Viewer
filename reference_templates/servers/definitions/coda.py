# ruff: noqa: F821, F706
"""Call the Coda API for document and table operations."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://coda.io/apis/v1"
DOCUMENTATION_URL = "https://coda.io/developers/apis/v1"


def main(
    operation: str = "",
    doc_id: str = "",
    table_id: str = "",
    row_id: str = "",
    column_id: str = "",
    data: str = "",
    query: str = "",
    limit: int = 100,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    CODA_API_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Coda API.

    Args:
        operation: Operation to perform (list_docs, get_doc, list_tables, get_table,
                   list_rows, get_row, create_row, update_row, delete_row, list_columns)
        doc_id: Document ID for document/table operations
        table_id: Table ID for table/row operations
        row_id: Row ID for get/update/delete row operations
        column_id: Column ID for filtering
        data: JSON data for create/update operations
        query: Query string for filtering rows
        limit: Maximum number of results (default: 100)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        CODA_API_TOKEN: API token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not CODA_API_TOKEN:
        return missing_secret_error("CODA_API_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="coda",
            title="Coda API",
            description=(
                "Access Coda documents, tables, and rows for collaborative "
                "data management."
            ),
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_docs",
                        "get_doc",
                        "list_tables",
                        "get_table",
                        "list_rows",
                        "get_row",
                        "create_row",
                        "update_row",
                        "delete_row",
                        "list_columns",
                    ],
                    required=True,
                ),
                FormField(
                    name="doc_id",
                    label="Document ID",
                    placeholder="abc123xyz",
                    help_text="Required for document/table operations",
                ),
                FormField(
                    name="table_id",
                    label="Table ID",
                    placeholder="grid-abc123",
                    help_text="Required for table/row operations",
                ),
                FormField(
                    name="row_id",
                    label="Row ID",
                    placeholder="i-abc123",
                    help_text="Required for get/update/delete row operations",
                ),
                FormField(
                    name="column_id",
                    label="Column ID",
                    placeholder="c-abc123",
                    help_text="Optional for filtering",
                ),
                FormField(
                    name="data",
                    label="Data (JSON)",
                    field_type="textarea",
                    placeholder='{"cells": [{"column": "c-abc", "value": "Hello"}]}',
                    help_text="JSON data for create/update operations",
                ),
                FormField(
                    name="query",
                    label="Query",
                    placeholder="Name contains John",
                    help_text="Optional query for filtering rows",
                ),
                FormField(
                    name="limit",
                    label="Limit",
                    default="100",
                    help_text="Maximum number of results",
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
                    "title": "List documents",
                    "code": 'operation: "list_docs"',
                },
                {
                    "title": "List tables",
                    "code": 'operation: "list_tables"\ndoc_id: "abc123xyz"',
                },
                {
                    "title": "List rows",
                    "code": 'operation: "list_rows"\ndoc_id: "abc123xyz"\ntable_id: "grid-abc123"',
                },
                {
                    "title": "Create row",
                    "code": (
                        'operation: "create_row"\ndoc_id: "abc123xyz"\n'
                        'table_id: "grid-abc123"\n'
                        'data: \'{"cells": [{"column": "c-abc", "value": "Hello"}]}\''
                    ),
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_docs",
        "get_doc",
        "list_tables",
        "get_table",
        "list_rows",
        "get_row",
        "create_row",
        "update_row",
        "delete_row",
        "list_columns",
    ]
    if operation not in valid_operations:
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}",
            error_type="validation_error",
        )

    # Build request based on operation
    method = "GET"
    url = API_BASE_URL
    payload = None
    params = {"limit": limit}

    if operation == "list_docs":
        url = f"{url}/docs"
    elif operation == "get_doc":
        if not doc_id:
            return error_response(
                "doc_id is required for get_doc operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}"
    elif operation == "list_tables":
        if not doc_id:
            return error_response(
                "doc_id is required for list_tables operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}/tables"
    elif operation == "get_table":
        if not doc_id or not table_id:
            return error_response(
                "doc_id and table_id are required for get_table operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}/tables/{table_id}"
    elif operation == "list_rows":
        if not doc_id or not table_id:
            return error_response(
                "doc_id and table_id are required for list_rows operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows"
        if query:
            params["query"] = query
    elif operation == "get_row":
        if not doc_id or not table_id or not row_id:
            return error_response(
                "doc_id, table_id, and row_id are required for get_row operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
    elif operation == "create_row":
        if not doc_id or not table_id or not data:
            return error_response(
                "doc_id, table_id, and data are required for create_row operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows"
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "update_row":
        if not doc_id or not table_id or not row_id or not data:
            return error_response(
                "doc_id, table_id, row_id, and data are required for update_row operation",
                error_type="validation_error",
            )
        method = "PUT"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            return error_response(
                f"Invalid JSON in data parameter: {str(e)}",
                error_type="validation_error",
            )
    elif operation == "delete_row":
        if not doc_id or not table_id or not row_id:
            return error_response(
                "doc_id, table_id, and row_id are required for delete_row operation",
                error_type="validation_error",
            )
        method = "DELETE"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
    elif operation == "list_columns":
        if not doc_id or not table_id:
            return error_response(
                "doc_id and table_id are required for list_columns operation",
                error_type="validation_error",
            )
        url = f"{url}/docs/{doc_id}/tables/{table_id}/columns"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
        }
        if params and method == "GET":
            preview["params"] = params
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {CODA_API_TOKEN}",
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
            params=params if method == "GET" else None,
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
