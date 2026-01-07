# ruff: noqa: F821, F706
"""Call the Coda API for document and table operations."""

from typing import Optional
from server_utils.external_api import (
    CredentialValidator,
    ExternalApiClient,
    HttpClientConfig,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
    generate_form,
    FormField,
)


API_BASE_URL = "https://coda.io/apis/v1"
DOCUMENTATION_URL = "https://coda.io/developers/apis/v1"

_OPERATIONS = {
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
}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "get_doc": ["doc_id"],
    "list_tables": ["doc_id"],
    "get_table": ["doc_id", "table_id"],
    "list_rows": ["doc_id", "table_id"],
    "get_row": ["doc_id", "table_id", "row_id"],
    "create_row": ["doc_id", "table_id", "data"],
    "update_row": ["doc_id", "table_id", "row_id", "data"],
    "delete_row": ["doc_id", "table_id", "row_id"],
    "list_columns": ["doc_id", "table_id"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


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
    if error := CredentialValidator.require_secret(CODA_API_TOKEN, "CODA_API_TOKEN"):
        return error

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
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {
            "doc_id": doc_id,
            "table_id": table_id,
            "row_id": row_id,
            "data": data,
        },
    ):
        return error

    # Parse JSON data for create/update operations
    payload = None
    if normalized_operation in {"create_row", "update_row"}:
        try:
            import json
            payload = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            from server_utils.external_api import validation_error
            return validation_error(
                f"Invalid JSON in data parameter: {str(e)}",
                field="data",
            )

    # Build request based on operation
    method = "GET"
    url = API_BASE_URL
    params = {"limit": limit}

    if normalized_operation == "list_docs":
        url = f"{url}/docs"
    elif normalized_operation == "get_doc":
        url = f"{url}/docs/{doc_id}"
    elif normalized_operation == "list_tables":
        url = f"{url}/docs/{doc_id}/tables"
    elif normalized_operation == "get_table":
        url = f"{url}/docs/{doc_id}/tables/{table_id}"
    elif normalized_operation == "list_rows":
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows"
        if query:
            params["query"] = query
    elif normalized_operation == "get_row":
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
    elif normalized_operation == "create_row":
        method = "POST"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows"
    elif normalized_operation == "update_row":
        method = "PUT"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
    elif normalized_operation == "delete_row":
        method = "DELETE"
        url = f"{url}/docs/{doc_id}/tables/{table_id}/rows/{row_id}"
    elif normalized_operation == "list_columns":
        url = f"{url}/docs/{doc_id}/tables/{table_id}/columns"

    # Dry run: return preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Bearer Token",
            params=params if method == "GET" else None,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

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
    except Exception as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Extract error message from Coda API response
    def extract_error(data):
        if isinstance(data, dict):
            return data.get("message", "Coda API error")
        return "Coda API error"

    return ResponseHandler.handle_json_response(response, extract_error)
