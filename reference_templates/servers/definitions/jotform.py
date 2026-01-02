# ruff: noqa: F821, F706
"""Call the Jotform API for forms and submissions."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.jotform.com"
DOCUMENTATION_URL = "https://api.jotform.com/docs/"


def main(
    operation: str = "",
    form_id: str = "",
    submission_id: str = "",
    form_title: str = "",
    question_text: str = "",
    limit: int = 20,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    JOTFORM_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Jotform API.

    Args:
        operation: Operation to perform (list_forms, get_form, create_form,
                   list_submissions, get_submission, list_questions, delete_form)
        form_id: Form ID for form operations
        submission_id: Submission ID for submission operations
        form_title: Title for form creation
        question_text: Question text for adding questions
        limit: Maximum number of results to return (default: 20)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        JOTFORM_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not JOTFORM_API_KEY:
        return missing_secret_error("JOTFORM_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="jotform",
            title="Jotform API",
            description="Access Jotform forms and submissions.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_forms",
                        "get_form",
                        "create_form",
                        "list_submissions",
                        "get_submission",
                        "list_questions",
                        "delete_form",
                    ],
                    required=True,
                ),
                FormField(
                    name="form_id",
                    label="Form ID",
                    placeholder="123456789012345",
                ),
                FormField(
                    name="submission_id",
                    label="Submission ID",
                    placeholder="987654321098765",
                ),
                FormField(
                    name="form_title",
                    label="Form Title",
                    placeholder="Customer Survey",
                    help_text="Required for create_form",
                ),
                FormField(
                    name="question_text",
                    label="Question Text",
                    placeholder="What is your name?",
                    help_text="Optional for form creation",
                ),
                FormField(
                    name="limit",
                    label="Limit",
                    default="20",
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
                    "title": "List forms",
                    "code": 'operation: "list_forms"',
                },
                {
                    "title": "Get form",
                    "code": 'operation: "get_form"\nform_id: "123456789012345"',
                },
                {
                    "title": "Create form",
                    "code": 'operation: "create_form"\nform_title: "Survey"',
                },
                {
                    "title": "List submissions",
                    "code": 'operation: "list_submissions"\nform_id: "123456789012345"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_forms",
        "get_form",
        "create_form",
        "list_submissions",
        "get_submission",
        "list_questions",
        "delete_form",
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
    params = {"apiKey": JOTFORM_API_KEY}

    if operation == "list_forms":
        url = f"{API_BASE_URL}/user/forms"
        params["limit"] = limit
    elif operation == "get_form":
        if not form_id:
            return error_response(
                "form_id is required for get_form operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/form/{form_id}"
    elif operation == "create_form":
        if not form_title:
            return error_response(
                "form_title is required for create_form operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/user/forms"
        payload = {
            "title": form_title,
        }
        if question_text:
            payload["questions[0][type]"] = "control_textbox"
            payload["questions[0][text]"] = question_text
    elif operation == "list_submissions":
        if not form_id:
            return error_response(
                "form_id is required for list_submissions operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/form/{form_id}/submissions"
        params["limit"] = limit
    elif operation == "get_submission":
        if not submission_id:
            return error_response(
                "submission_id is required for get_submission operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/submission/{submission_id}"
    elif operation == "list_questions":
        if not form_id:
            return error_response(
                "form_id is required for list_questions operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/form/{form_id}/questions"
    elif operation == "delete_form":
        if not form_id:
            return error_response(
                "form_id is required for delete_form operation",
                error_type="validation_error",
            )
        method = "DELETE"
        url = f"{API_BASE_URL}/form/{form_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "params": {"apiKey": "[REDACTED]"},
        }
        if limit and operation in ["list_forms", "list_submissions"]:
            preview["params"]["limit"] = limit
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Accept": "application/json",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            data=payload if payload else None,
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
