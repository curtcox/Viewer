# ruff: noqa: F821, F706
"""Call the Postmark API for transactional email delivery."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.postmarkapp.com"
DOCUMENTATION_URL = "https://postmarkapp.com/developer"


def main(
    operation: str = "",
    to_email: str = "",
    from_email: str = "",
    subject: str = "",
    text_body: str = "",
    html_body: str = "",
    template_id: str = "",
    message_id: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    POSTMARK_SERVER_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Postmark API.

    Args:
        operation: Operation to perform (send_email, send_template_email, get_message,
                   list_bounces, get_stats, list_templates, get_template)
        to_email: Recipient email address
        from_email: Sender email address (must be verified in Postmark)
        subject: Email subject
        text_body: Plain text email body
        html_body: HTML email body
        template_id: Template ID for template-based emails
        message_id: Message ID for retrieving message details
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        POSTMARK_SERVER_TOKEN: Server token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not POSTMARK_SERVER_TOKEN:
        return missing_secret_error("POSTMARK_SERVER_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="postmark",
            title="Postmark API",
            description="Send transactional email via Postmark.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "send_email",
                        "send_template_email",
                        "get_message",
                        "list_bounces",
                        "get_stats",
                        "list_templates",
                        "get_template",
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
                    name="text_body",
                    label="Text Body",
                    field_type="textarea",
                    placeholder="Plain text email body",
                ),
                FormField(
                    name="html_body",
                    label="HTML Body",
                    field_type="textarea",
                    placeholder="<h1>HTML email body</h1>",
                ),
                FormField(
                    name="template_id", label="Template ID", placeholder="123456"
                ),
                FormField(
                    name="message_id",
                    label="Message ID",
                    placeholder="abc-123-def-456",
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
                    "title": "Send email",
                    "code": 'operation: "send_email"\nto_email: "user@example.com"\nfrom_email: "sender@example.com"\nsubject: "Hello"\ntext_body: "Test message"',
                },
                {"title": "List templates", "code": 'operation: "list_templates"'},
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "send_email",
        "send_template_email",
        "get_message",
        "list_bounces",
        "get_stats",
        "list_templates",
        "get_template",
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

    if operation == "send_email":
        if not to_email or not from_email or not subject:
            return error_response(
                "to_email, from_email, and subject are required for send_email operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/email"
        payload = {
            "To": to_email,
            "From": from_email,
            "Subject": subject,
        }
        if text_body:
            payload["TextBody"] = text_body
        if html_body:
            payload["HtmlBody"] = html_body
    elif operation == "send_template_email":
        if not to_email or not from_email or not template_id:
            return error_response(
                "to_email, from_email, and template_id are required for send_template_email operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/email/withTemplate"
        payload = {
            "To": to_email,
            "From": from_email,
            "TemplateId": template_id,
        }
    elif operation == "get_message":
        if not message_id:
            return error_response(
                "message_id is required for get_message operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/messages/outbound/{message_id}/details"
    elif operation == "list_bounces":
        url = f"{API_BASE_URL}/bounces"
    elif operation == "get_stats":
        url = f"{API_BASE_URL}/stats/outbound"
    elif operation == "list_templates":
        url = f"{API_BASE_URL}/templates"
    elif operation == "get_template":
        if not template_id:
            return error_response(
                "template_id is required for get_template operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/templates/{template_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"X-Postmark-Server-Token": "[REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "X-Postmark-Server-Token": POSTMARK_SERVER_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
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
