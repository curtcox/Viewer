# ruff: noqa: F821, F706
"""Call the Docparser API for document parsing operations."""

from __future__ import annotations

import base64
from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    missing_secret_error,
    validation_error,
    generate_form,
    validate_and_build_payload,
    FormField,
)


API_BASE_URL = "https://api.docparser.com/v1"
DOCUMENTATION_URL = "https://dev.docparser.com/"


def _build_basic_auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


_OPERATIONS = {
    "list_parsers": OperationDefinition(
        payload_builder=lambda **_: {
            "method": "GET",
            "url": f"{API_BASE_URL}/parsers",
            "params": None,
            "payload": None,
        },
    ),
    "upload_document": OperationDefinition(
        required=(
            RequiredField("parser_id"),
            RequiredField("file_url", message="file_url is required"),
        ),
        payload_builder=lambda parser_id, file_url, **_: {
            "method": "POST",
            "url": f"{API_BASE_URL}/document/upload/{parser_id}",
            "params": None,
            "payload": {"url": file_url},
        },
    ),
    "list_documents": OperationDefinition(
        required=(RequiredField("parser_id", message="parser_id is required"),),
        payload_builder=lambda parser_id, **_: {
            "method": "GET",
            "url": f"{API_BASE_URL}/results/{parser_id}",
            "params": None,
            "payload": None,
        },
    ),
    "get_document": OperationDefinition(
        required=(
            RequiredField("document_id", message="document_id is required"),
            RequiredField("parser_id", message="parser_id is required"),
        ),
        payload_builder=lambda parser_id, document_id, **_: {
            "method": "GET",
            "url": f"{API_BASE_URL}/results/{parser_id}/{document_id}",
            "params": None,
            "payload": None,
        },
    ),
    "get_parsed_data": OperationDefinition(
        required=(
            RequiredField("document_id", message="document_id is required"),
            RequiredField("parser_id", message="parser_id is required"),
        ),
        payload_builder=lambda parser_id, document_id, output_format, **_: {
            "method": "GET",
            "url": f"{API_BASE_URL}/results/{parser_id}/{document_id}",
            "params": {"format": output_format},
            "payload": None,
        },
    ),
    "delete_document": OperationDefinition(
        required=(
            RequiredField("document_id", message="document_id is required"),
            RequiredField("parser_id", message="parser_id is required"),
        ),
        payload_builder=lambda parser_id, document_id, **_: {
            "method": "DELETE",
            "url": f"{API_BASE_URL}/results/{parser_id}/{document_id}",
            "params": None,
            "payload": None,
        },
    ),
}


def main(
    operation: str = "",
    parser_id: str = "",
    document_id: str = "",
    file_url: str = "",
    output_format: str = "object",
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
        output_format: Output format for parsed data (object, flat, csv)
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
                    name="output_format",
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

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        parser_id=parser_id,
        document_id=document_id,
        file_url=file_url,
        output_format=output_format,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    if result is None:
        return validation_error("Unsupported operation", field="operation")

    method = result["method"]
    url = result["url"]
    params = result["params"]
    payload = result["payload"]

    # Dry run preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "params": params,
            "payload": payload,
            "auth": "Basic [REDACTED]",
        }
        return {"output": preview, "content_type": "application/json"}

    # Create HTTP client
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Content-Type": "application/json",
        "Authorization": _build_basic_auth_header(DOCPARSER_API_KEY),
    }

    result = execute_json_request(
        client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        request_error_message="Docparser API request failed",
        empty_response_statuses=(204,),
        empty_response_output={"success": True},
    )
    if "output" in result:
        result["content_type"] = "application/json"
    return result
