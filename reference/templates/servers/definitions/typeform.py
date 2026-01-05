# ruff: noqa: F821, F706
"""Call the Typeform API for forms and responses."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.typeform.com"
DOCUMENTATION_URL = "https://developer.typeform.com/get-started/"


def main(
    operation: str = "",
    form_id: str = "",
    response_id: str = "",
    title: str = "",
    workspace_id: str = "",
    page_size: int = 10,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    TYPEFORM_ACCESS_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Typeform API.

    Args:
        operation: Operation to perform (list_forms, get_form, create_form,
                   list_responses, get_response, delete_form, list_workspaces)
        form_id: Form ID for form operations
        response_id: Response ID for response operations
        title: Title for form creation
        workspace_id: Workspace ID for form creation or listing
        page_size: Number of results per page (default: 10)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        TYPEFORM_ACCESS_TOKEN: Access token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not TYPEFORM_ACCESS_TOKEN:
        return missing_secret_error("TYPEFORM_ACCESS_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="typeform",
            title="Typeform API",
            description="Access Typeform forms and responses.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_forms",
                        "get_form",
                        "create_form",
                        "list_responses",
                        "get_response",
                        "delete_form",
                        "list_workspaces",
                    ],
                    required=True,
                ),
                FormField(name="form_id", label="Form ID", placeholder="abc123"),
                FormField(name="response_id", label="Response ID", placeholder="xyz789"),
                FormField(
                    name="title",
                    label="Form Title",
                    placeholder="My Survey",
                    help_text="Required for create_form",
                ),
                FormField(
                    name="workspace_id",
                    label="Workspace ID",
                    placeholder="workspace123",
                    help_text="Optional for create_form and list_forms",
                ),
                FormField(
                    name="page_size",
                    label="Page Size",
                    default="10",
                    help_text="Number of results per page",
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
                    "title": "List forms",
                    "code": 'operation: "list_forms"',
                },
                {
                    "title": "Get form",
                    "code": 'operation: "get_form"\nform_id: "abc123"',
                },
                {
                    "title": "Create form",
                    "code": 'operation: "create_form"\ntitle: "Customer Feedback"',
                },
                {
                    "title": "List responses",
                    "code": 'operation: "list_responses"\nform_id: "abc123"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_forms",
        "get_form",
        "create_form",
        "list_responses",
        "get_response",
        "delete_form",
        "list_workspaces",
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
    params = {}

    if operation == "list_forms":
        url = f"{API_BASE_URL}/forms"
        params["page_size"] = page_size
        if workspace_id:
            params["workspace_id"] = workspace_id
    elif operation == "get_form":
        if not form_id:
            return error_response(
                "form_id is required for get_form operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/forms/{form_id}"
    elif operation == "create_form":
        if not title:
            return error_response(
                "title is required for create_form operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/forms"
        payload = {
            "title": title,
            "type": "form",
        }
        if workspace_id:
            payload["workspace"] = {"href": f"{API_BASE_URL}/workspaces/{workspace_id}"}
    elif operation == "list_responses":
        if not form_id:
            return error_response(
                "form_id is required for list_responses operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/forms/{form_id}/responses"
        params["page_size"] = page_size
    elif operation == "get_response":
        if not form_id or not response_id:
            return error_response(
                "form_id and response_id are required for get_response operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/forms/{form_id}/responses/{response_id}"
    elif operation == "delete_form":
        if not form_id:
            return error_response(
                "form_id is required for delete_form operation",
                error_type="validation_error",
            )
        method = "DELETE"
        url = f"{API_BASE_URL}/forms/{form_id}"
    elif operation == "list_workspaces":
        url = f"{API_BASE_URL}/workspaces"
        params["page_size"] = page_size

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
        }
        if params:
            preview["params"] = params
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {TYPEFORM_ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            params=params if params else None,
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
