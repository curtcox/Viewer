# ruff: noqa: F821, F706
"""Call the Parseur API for email and document parsing."""

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


API_BASE_URL = "https://api.parseur.com/v1"
DOCUMENTATION_URL = "https://help.parseur.com/en/articles/5154126-parseur-api"


def main(
    operation: str = "",
    inbox_id: str = "",
    document_id: str = "",
    limit: int = 100,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    PARSEUR_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Parseur API.

    Args:
        operation: Operation to perform (list_inboxes, get_inbox, list_documents,
                   get_document, get_parsed_data, delete_document)
        inbox_id: Inbox ID for document operations
        document_id: Document ID for document-specific operations
        limit: Maximum number of results (default: 100)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        PARSEUR_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not PARSEUR_API_KEY:
        return missing_secret_error("PARSEUR_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="parseur",
            title="Parseur API",
            description=(
                "Parse emails and documents automatically with Parseur: extract data from "
                "emails, PDFs, and other documents using custom templates."
            ),
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_inboxes",
                        "get_inbox",
                        "list_documents",
                        "get_document",
                        "get_parsed_data",
                        "delete_document",
                    ],
                    required=True,
                ),
                FormField(
                    name="inbox_id",
                    label="Inbox ID",
                    placeholder="inbox123",
                    help_text="Required for inbox-specific operations",
                ),
                FormField(
                    name="document_id",
                    label="Document ID",
                    placeholder="doc123",
                    help_text="Required for document-specific operations",
                ),
                FormField(
                    name="limit",
                    label="Limit",
                    placeholder="100",
                    help_text="Maximum number of results to return",
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
                    "title": "List Inboxes",
                    "code": 'operation=list_inboxes',
                },
                {
                    "title": "List Documents",
                    "code": 'operation=list_documents&inbox_id=inbox123',
                },
                {
                    "title": "Get Parsed Data",
                    "code": 'operation=get_parsed_data&inbox_id=inbox123&document_id=doc123',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_inboxes", "get_inbox", "list_documents",
        "get_document", "get_parsed_data", "delete_document"
    ]
    if operation not in valid_operations:
        return validation_error(
            f"Invalid operation: {operation}. Must be one of {valid_operations}"
        )

    # Operation-specific validation
    if operation in ["get_inbox", "list_documents"]:
        if not inbox_id:
            return validation_error(f"inbox_id is required for {operation}")

    if operation in ["get_document", "get_parsed_data", "delete_document"]:
        if not inbox_id:
            return validation_error(f"inbox_id is required for {operation}")
        if not document_id:
            return validation_error(f"document_id is required for {operation}")

    # Dry run preview
    if dry_run:
        preview = {
            "operation": operation,
            "api_endpoint": API_BASE_URL,
            "dry_run": True,
        }
        
        if inbox_id:
            preview["inbox_id"] = inbox_id
        if document_id:
            preview["document_id"] = document_id
        if limit:
            preview["limit"] = limit

        return {"output": preview, "content_type": "application/json"}

    # Create HTTP client
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Token {PARSEUR_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # Build request based on operation
        if operation == "list_inboxes":
            response = client.get(
                f"{API_BASE_URL}/inboxes",
                headers=headers,
                params={"limit": limit}
            )
        
        elif operation == "get_inbox":
            response = client.get(
                f"{API_BASE_URL}/inboxes/{inbox_id}",
                headers=headers
            )
        
        elif operation == "list_documents":
            response = client.get(
                f"{API_BASE_URL}/inboxes/{inbox_id}/documents",
                headers=headers,
                params={"limit": limit}
            )
        
        elif operation == "get_document":
            response = client.get(
                f"{API_BASE_URL}/inboxes/{inbox_id}/documents/{document_id}",
                headers=headers
            )
        
        elif operation == "get_parsed_data":
            response = client.get(
                f"{API_BASE_URL}/inboxes/{inbox_id}/documents/{document_id}/parsed",
                headers=headers
            )
        
        elif operation == "delete_document":
            response = client.delete(
                f"{API_BASE_URL}/inboxes/{inbox_id}/documents/{document_id}",
                headers=headers
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
            message=f"Parseur API request failed: {error_detail}",
            error_type="api_error",
            status_code=status_code,
        )
    except Exception as e:
        return error_response(
            message=f"Unexpected error: {str(e)}",
            error_type="api_error",
        )
