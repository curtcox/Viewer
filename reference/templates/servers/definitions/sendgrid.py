# ruff: noqa: F821, F706
"""Call the SendGrid API for transactional and marketing email."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.sendgrid.com/v3"
DOCUMENTATION_URL = "https://docs.sendgrid.com/api-reference"


def main(
    operation: str = "",
    to_email: str = "",
    from_email: str = "",
    subject: str = "",
    content: str = "",
    template_id: str = "",
    list_id: str = "",
    contact_id: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    SENDGRID_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the SendGrid API.

    Args:
        operation: Operation to perform (send_mail, list_templates, get_template,
                   list_contacts, get_contact, add_contact, list_lists, get_list)
        to_email: Recipient email address for sending
        from_email: Sender email address
        subject: Email subject
        content: Email content (plain text or HTML)
        template_id: Template ID for template operations
        list_id: List ID for list operations
        contact_id: Contact ID for contact operations
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        SENDGRID_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not SENDGRID_API_KEY:
        return missing_secret_error("SENDGRID_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="sendgrid",
            title="SendGrid API",
            description="Send transactional and marketing email via SendGrid.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "send_mail",
                        "list_templates",
                        "get_template",
                        "list_contacts",
                        "get_contact",
                        "add_contact",
                        "list_lists",
                        "get_list",
                    ],
                    required=True,
                ),
                FormField(
                    name="to_email", label="To Email", placeholder="user@example.com"
                ),
                FormField(
                    name="from_email",
                    label="From Email",
                    placeholder="sender@example.com",
                ),
                FormField(
                    name="subject", label="Subject", placeholder="Email subject"
                ),
                FormField(
                    name="content",
                    label="Content",
                    field_type="textarea",
                    placeholder="Email body",
                ),
                FormField(
                    name="template_id", label="Template ID", placeholder="d-abc123"
                ),
                FormField(name="list_id", label="List ID", placeholder="abc123"),
                FormField(name="contact_id", label="Contact ID", placeholder="abc123"),
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
                    "title": "Send email",
                    "code": 'operation: "send_mail"\nto_email: "user@example.com"\nfrom_email: "sender@example.com"\nsubject: "Hello"\ncontent: "Test message"',
                },
                {"title": "List templates", "code": 'operation: "list_templates"'},
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "send_mail",
        "list_templates",
        "get_template",
        "list_contacts",
        "get_contact",
        "add_contact",
        "list_lists",
        "get_list",
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

    if operation == "send_mail":
        if not to_email or not from_email or not subject:
            return error_response(
                "to_email, from_email, and subject are required for send_mail operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/mail/send"
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": content or ""}],
        }
    elif operation == "list_templates":
        url = f"{API_BASE_URL}/templates"
    elif operation == "get_template":
        if not template_id:
            return error_response(
                "template_id is required for get_template operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/templates/{template_id}"
    elif operation == "list_contacts":
        url = f"{API_BASE_URL}/marketing/contacts"
    elif operation == "get_contact":
        if not contact_id:
            return error_response(
                "contact_id is required for get_contact operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/marketing/contacts/{contact_id}"
    elif operation == "add_contact":
        if not to_email:
            return error_response(
                "to_email is required for add_contact operation",
                error_type="validation_error",
            )
        method = "PUT"
        url = f"{API_BASE_URL}/marketing/contacts"
        payload = {"contacts": [{"email": to_email}]}
    elif operation == "list_lists":
        url = f"{API_BASE_URL}/marketing/lists"
    elif operation == "get_list":
        if not list_id:
            return error_response(
                "list_id is required for get_list operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/marketing/lists/{list_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = client.request(
            method=method, url=url, headers=headers, json=payload, timeout=timeout
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
