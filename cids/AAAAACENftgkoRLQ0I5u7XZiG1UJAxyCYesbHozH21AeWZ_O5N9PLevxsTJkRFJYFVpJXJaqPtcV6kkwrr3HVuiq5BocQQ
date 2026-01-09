# ruff: noqa: F821, F706
"""Call the Postmark API for transactional email delivery."""

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    FormField,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    generate_form,
    missing_secret_error,
    validate_and_build_payload,
    validation_error,
)


API_BASE_URL = "https://api.postmarkapp.com"
DOCUMENTATION_URL = "https://postmarkapp.com/developer"


_OPERATIONS = {
    "send_email": OperationDefinition(
        required=(
            RequiredField("to_email"),
            RequiredField("from_email"),
            RequiredField("subject"),
        ),
        payload_builder=lambda to_email, from_email, subject, text_body, html_body, **_: {
            "To": to_email,
            "From": from_email,
            "Subject": subject,
            **({"TextBody": text_body} if text_body else {}),
            **({"HtmlBody": html_body} if html_body else {}),
        },
    ),
    "send_template_email": OperationDefinition(
        required=(
            RequiredField("to_email"),
            RequiredField("from_email"),
            RequiredField("template_id"),
        ),
        payload_builder=lambda to_email, from_email, template_id, **_: {
            "To": to_email,
            "From": from_email,
            "TemplateId": template_id,
        },
    ),
    "get_message": OperationDefinition(required=(RequiredField("message_id"),)),
    "list_bounces": OperationDefinition(),
    "get_stats": OperationDefinition(),
    "list_templates": OperationDefinition(),
    "get_template": OperationDefinition(required=(RequiredField("template_id"),)),
}

_ENDPOINT_BUILDERS = {
    "send_email": lambda **_: "email",
    "send_template_email": lambda **_: "email/withTemplate",
    "get_message": lambda message_id, **_: f"messages/outbound/{message_id}/details",
    "list_bounces": lambda **_: "bounces",
    "get_stats": lambda **_: "stats/outbound",
    "list_templates": lambda **_: "templates",
    "get_template": lambda template_id, **_: f"templates/{template_id}",
}

_METHODS = {
    "send_email": "POST",
    "send_template_email": "POST",
}


def _build_preview(
    *,
    operation: str,
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "method": method,
        "url": url,
        "headers": {"X-Postmark-Server-Token": "[REDACTED]"},
    }
    if payload:
        preview["payload"] = payload
    return preview


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
    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        to_email=to_email,
        from_email=from_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        template_id=template_id,
        message_id=message_id,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    endpoint = _ENDPOINT_BUILDERS[operation](
        message_id=message_id,
        template_id=template_id,
    )
    url = f"{API_BASE_URL}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    # Dry run: return preview
    if dry_run:
        preview = _build_preview(
            operation=operation,
            method=method,
            url=url,
            payload=payload,
        )
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

    return execute_json_request(
        client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        request_error_message="Postmark request failed",
    )
