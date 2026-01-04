# ruff: noqa: F821, F706
"""Call the PDF.co API for PDF processing operations."""

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
import json
import requests


API_BASE_URL = "https://api.pdf.co/v1"
DOCUMENTATION_URL = "https://developer.pdf.co/"


def main(
    operation: str = "",
    url: str = "",
    file_url: str = "",
    pages: str = "",
    output_format: str = "",
    template: str = "",
    fields: str = "",
    async_mode: bool = False,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    PDFCO_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the PDF.co API.

    Args:
        operation: Operation to perform (pdf_to_text, pdf_to_json, pdf_split,
                   pdf_merge, pdf_to_html, pdf_info, pdf_forms_fill, barcode_read)
        url: URL of PDF file to process
        file_url: Alternative name for URL parameter
        pages: Page range or numbers (e.g., "1-3" or "1,3,5")
        output_format: Output format for extraction (txt, json, html)
        template: Template for data extraction
        fields: JSON fields for form filling
        async_mode: If True, process asynchronously
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        PDFCO_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not PDFCO_API_KEY:
        return missing_secret_error("PDFCO_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="pdfco",
            title="PDF.co API",
            description=(
                "Process PDFs with PDF.co API: extract text, split, merge, "
                "fill forms, read barcodes, and more."
            ),
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "pdf_to_text",
                        "pdf_to_json",
                        "pdf_split",
                        "pdf_merge",
                        "pdf_to_html",
                        "pdf_info",
                        "pdf_forms_fill",
                        "barcode_read",
                    ],
                    required=True,
                ),
                FormField(
                    name="url",
                    label="PDF URL",
                    placeholder="https://example.com/document.pdf",
                    help_text="URL of PDF file to process",
                    required=True,
                ),
                FormField(
                    name="pages",
                    label="Pages",
                    placeholder="1-3 or 1,3,5",
                    help_text="Page range or specific pages (optional)",
                ),
                FormField(
                    name="output_format",
                    label="Output Format",
                    placeholder="txt, json, html",
                    help_text="Format for extracted content (optional)",
                ),
                FormField(
                    name="fields",
                    label="Form Fields (JSON)",
                    field_type="textarea",
                    placeholder='{"name": "John", "email": "john@example.com"}',
                    help_text="Fields for form filling (pdf_forms_fill only)",
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
                    "title": "Extract Text from PDF",
                    "code": 'operation=pdf_to_text&url=https://example.com/doc.pdf',
                },
                {
                    "title": "Get PDF Info",
                    "code": 'operation=pdf_info&url=https://example.com/doc.pdf',
                },
                {
                    "title": "Read Barcodes",
                    "code": 'operation=barcode_read&url=https://example.com/doc.pdf',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "pdf_to_text", "pdf_to_json", "pdf_split", "pdf_merge",
        "pdf_to_html", "pdf_info", "pdf_forms_fill", "barcode_read"
    ]
    if operation not in valid_operations:
        return validation_error(
            f"Invalid operation: {operation}. Must be one of {valid_operations}"
        )

    # Use url or file_url
    pdf_url = url or file_url
    if not pdf_url:
        return validation_error("url or file_url is required")

    # Parse fields if provided
    parsed_fields = {}
    if fields:
        try:
            parsed_fields = json.loads(fields)
        except json.JSONDecodeError as e:
            return validation_error(f"Invalid JSON in fields: {e}")

    # Dry run preview
    if dry_run:
        preview = {
            "operation": operation,
            "api_endpoint": API_BASE_URL,
            "pdf_url": pdf_url,
            "dry_run": True,
        }
        
        if pages:
            preview["pages"] = pages
        if output_format:
            preview["output_format"] = output_format
        if parsed_fields:
            preview["fields"] = parsed_fields

        return {"output": preview, "content_type": "application/json"}

    # Create HTTP client
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "x-api-key": PDFCO_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        # Build request based on operation
        endpoint_map = {
            "pdf_to_text": "pdf/convert/to/text",
            "pdf_to_json": "pdf/convert/to/json",
            "pdf_split": "pdf/split",
            "pdf_merge": "pdf/merge",
            "pdf_to_html": "pdf/convert/to/html",
            "pdf_info": "pdf/info",
            "pdf_forms_fill": "pdf/edit/add",
            "barcode_read": "barcode/read/from/pdf",
        }
        
        endpoint = endpoint_map.get(operation)
        if not endpoint:
            return validation_error(f"Unsupported operation: {operation}")

        payload = {"url": pdf_url}
        
        if pages:
            payload["pages"] = pages
        if output_format:
            payload["outputFormat"] = output_format
        if async_mode:
            payload["async"] = True
        if operation == "pdf_forms_fill" and parsed_fields:
            payload["fields"] = parsed_fields

        response = client.post(
            f"{API_BASE_URL}/{endpoint}",
            headers=headers,
            json=payload
        )
        
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
            message=f"PDF.co API request failed: {error_detail}",
            error_type="api_error",
            status_code=status_code,
        )
    except Exception as e:
        return error_response(
            message=f"Unexpected error: {str(e)}",
            error_type="api_error",
        )
