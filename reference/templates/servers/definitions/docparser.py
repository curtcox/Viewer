# ruff: noqa: F821, F706
"""Call the Docparser API for document parsing operations."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    validation_error,
    generate_form,
    FormField,
)
import requests


API_BASE_URL = "https://api.docparser.com/v1"
DOCUMENTATION_URL = "https://dev.docparser.com/"


def main(
    operation: str = "",
    parser_id: str = "",
    document_id: str = "",
    file_url: str = "",
    format: str = "object",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    DOCPARSER_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Docparser API.

    Args:
        operation: Operation to perform (list_parsers, upload_document,
                   get_document, list_documents, get_parsed_data, delete_document)
        parser_id: Parser ID for document operations
        document_id: Document ID for document-specific operations
        file_url: URL of document to upload
        format: Output format for parsed data (object, flat, csv)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        DOCPARSER_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not DOCPARSER_API_KEY:
        return missing_secret_error("DOCPARSER_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="docparser",
            title="Docparser API",
            description=(
                "Parse documents automatically with Docparser: extract data from "
                "invoices, receipts, and other structured documents."
            ),
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_parsers",
                        "upload_document",
                        "get_document",
                        "list_documents",
                        "get_parsed_data",
                        "delete_document",
                    ],
                    required=True,
                ),
                FormField(
                    name="parser_id",
                    label="Parser ID",
                    placeholder="parser123",
                    help_text="Required for document operations",
                ),
                FormField(
                    name="document_id",
                    label="Document ID",
                    placeholder="doc123",
                    help_text="Required for document-specific operations",
                ),
                FormField(
                    name="file_url",
                    label="File URL",
                    placeholder="https://example.com/invoice.pdf",
                    help_text="URL of document to upload",
                ),
                FormField(
                    name="format",
                    label="Output Format",
                    field_type="select",
                    options=["object", "flat", "csv"],
                    default="object",
                    help_text="Format for parsed data output",
                ),
                FormField(
                    name="dry_run",
                    label="Dry Run",
                    field_type="select",
                    options=["true", "false"],
                    default="true",
                    help_text="Preview the request without executing",
                ),
            ],
            examples=[
                {
                    "title": "List Parsers",
                    "code": 'operation=list_parsers',
                },
                {
                    "title": "Upload Document",
                    "code": 'operation=upload_document&parser_id=parser123&file_url=https://example.com/invoice.pdf',
                },
                {
                    "title": "Get Parsed Data",
                    "code": 'operation=get_parsed_data&parser_id=parser123&document_id=doc123',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_parsers", "upload_document", "get_document",
        "list_documents", "get_parsed_data", "delete_document"
    ]
    if operation not in valid_operations:
        return validation_error(
            f"Invalid operation: {operation}. Must be one of {valid_operations}"
        )

    # Operation-specific validation
    if operation in ["upload_document", "list_documents", "get_parsed_data"]:
        if not parser_id:
            return validation_error(f"parser_id is required for {operation}")

    if operation == "upload_document" and not file_url:
        return validation_error("file_url is required for upload_document")

    if operation in ["get_document", "get_parsed_data", "delete_document"]:
        if not document_id:
            return validation_error(f"document_id is required for {operation}")
        if not parser_id:
            return validation_error(f"parser_id is required for {operation}")

    # Dry run preview
    if dry_run:
        preview = {
            "operation": operation,
            "api_endpoint": API_BASE_URL,
            "dry_run": True,
        }
        
        if parser_id:
            preview["parser_id"] = parser_id
        if document_id:
            preview["document_id"] = document_id
        if file_url:
            preview["file_url"] = file_url
        if format:
            preview["format"] = format

        return {"output": preview, "content_type": "application/json"}

    # Create HTTP client
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    # Use Basic Auth with API key
    auth = (DOCPARSER_API_KEY, "")
    headers = {"Content-Type": "application/json"}

    try:
        # Build request based on operation
        if operation == "list_parsers":
            response = client.get(f"{API_BASE_URL}/parsers", headers=headers, auth=auth)
        
        elif operation == "upload_document":
            payload = {"url": file_url}
            response = client.post(
                f"{API_BASE_URL}/document/upload/{parser_id}",
                headers=headers,
                json=payload,
                auth=auth
            )
        
        elif operation == "list_documents":
            response = client.get(
                f"{API_BASE_URL}/results/{parser_id}",
                headers=headers,
                auth=auth
            )
        
        elif operation == "get_document":
            response = client.get(
                f"{API_BASE_URL}/results/{parser_id}/{document_id}",
                headers=headers,
                auth=auth
            )
        
        elif operation == "get_parsed_data":
            response = client.get(
                f"{API_BASE_URL}/results/{parser_id}/{document_id}",
                headers=headers,
                params={"format": format},
                auth=auth
            )
        
        elif operation == "delete_document":
            response = client.delete(
                f"{API_BASE_URL}/results/{parser_id}/{document_id}",
                headers=headers,
                auth=auth
            )
        
        else:
            return validation_error(f"Unsupported operation: {operation}")

        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}

    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = ""
        if hasattr(e, "response") and e.response:
            try:
                error_detail = e.response.text
            except Exception:
                error_detail = str(e)
        else:
            error_detail = str(e)
        
        return error_response(
            message=f"Docparser API request failed: {error_detail}",
            error_type="api_error",
            status_code=status_code,
        )
    except Exception as e:
        return error_response(
            message=f"Unexpected error: {str(e)}",
            error_type="api_error",
        )
