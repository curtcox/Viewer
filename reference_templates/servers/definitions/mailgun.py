# ruff: noqa: F821, F706
"""Call the Mailgun API for email delivery and management."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


DOCUMENTATION_URL = "https://documentation.mailgun.com/en/latest/api_reference.html"


def main(
    operation: str = "",
    to_email: str = "",
    from_email: str = "",
    subject: str = "",
    text: str = "",
    html: str = "",
    tag: str = "",
    event: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    MAILGUN_API_KEY: str,
    MAILGUN_DOMAIN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Mailgun API.

    Args:
        operation: Operation to perform (send_message, get_message, list_events,
                   get_stats, list_domains, validate_email)
        to_email: Recipient email address
        from_email: Sender email address
        subject: Email subject
        text: Plain text email content
        html: HTML email content
        tag: Tag for filtering events
        event: Event type for filtering (delivered, failed, opened, etc.)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        MAILGUN_API_KEY: API key for authentication (from secrets)
        MAILGUN_DOMAIN: Mailgun domain (e.g., mg.example.com)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not MAILGUN_API_KEY:
        return missing_secret_error("MAILGUN_API_KEY")
    if not MAILGUN_DOMAIN:
        return missing_secret_error("MAILGUN_DOMAIN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="mailgun",
            title="Mailgun API",
            description="Send and manage emails with Mailgun.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "send_message",
                        "get_message",
                        "list_events",
                        "get_stats",
                        "list_domains",
                        "validate_email",
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
                    name="text",
                    label="Text Content",
                    field_type="textarea",
                    placeholder="Plain text email body",
                ),
                FormField(
                    name="html",
                    label="HTML Content",
                    field_type="textarea",
                    placeholder="<h1>HTML email body</h1>",
                ),
                FormField(name="tag", label="Tag", placeholder="newsletter"),
                FormField(
                    name="event",
                    label="Event Type",
                    placeholder="delivered, failed, opened",
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
                    "title": "Send message",
                    "code": 'operation: "send_message"\nto_email: "user@example.com"\nfrom_email: "sender@example.com"\nsubject: "Hello"\ntext: "Test message"',
                },
                {"title": "List events", "code": 'operation: "list_events"'},
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "send_message",
        "get_message",
        "list_events",
        "get_stats",
        "list_domains",
        "validate_email",
    ]
    if operation not in valid_operations:
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}",
            error_type="validation_error",
        )

    # Build request based on operation
    api_base = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}"
    method = "GET"
    url = api_base
    payload = None

    if operation == "send_message":
        if not to_email or not from_email or not subject:
            return error_response(
                "to_email, from_email, and subject are required for send_message operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{api_base}/messages"
        payload = {
            "to": to_email,
            "from": from_email,
            "subject": subject,
        }
        if text:
            payload["text"] = text
        if html:
            payload["html"] = html
        if tag:
            payload["o:tag"] = tag
    elif operation == "get_message":
        # Requires message key - not fully implemented
        url = f"{api_base}/events"
    elif operation == "list_events":
        url = f"{api_base}/events"
        if event:
            url += f"?event={event}"
    elif operation == "get_stats":
        url = f"{api_base}/stats/total"
    elif operation == "list_domains":
        url = "https://api.mailgun.net/v3/domains"
    elif operation == "validate_email":
        if not to_email:
            return error_response(
                "to_email is required for validate_email operation",
                error_type="validation_error",
            )
        url = f"https://api.mailgun.net/v4/address/validate?address={to_email}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Basic [REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    # Mailgun uses Basic auth with "api" as username
    import base64

    auth_string = base64.b64encode(f"api:{MAILGUN_API_KEY}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_string}",
    }

    # For send_message, use form data not JSON
    if operation == "send_message":
        try:
            response = client.request(
                method=method, url=url, headers=headers, data=payload, timeout=timeout
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
    else:
        try:
            response = client.request(
                method=method, url=url, headers=headers, timeout=timeout
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
