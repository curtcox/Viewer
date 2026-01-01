# ruff: noqa: F821, F706
"""Call the MailerLite API for email marketing."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://connect.mailerlite.com/api"
DOCUMENTATION_URL = "https://developers.mailerlite.com/docs"


def main(
    operation: str = "",
    subscriber_id: str = "",
    email: str = "",
    fields: Optional[str] = None,
    group_id: str = "",
    campaign_id: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    MAILERLITE_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the MailerLite API.

    Args:
        operation: Operation to perform (list_subscribers, get_subscriber, create_subscriber,
                   update_subscriber, list_groups, get_group, list_campaigns, get_campaign)
        subscriber_id: Subscriber ID for subscriber operations
        email: Email address for subscriber creation/update
        fields: JSON string of custom fields for subscriber
        group_id: Group ID for group operations
        campaign_id: Campaign ID for campaign operations
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        MAILERLITE_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not MAILERLITE_API_KEY:
        return missing_secret_error("MAILERLITE_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="mailerlite",
            title="MailerLite API",
            description="Access MailerLite email marketing platform.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_subscribers",
                        "get_subscriber",
                        "create_subscriber",
                        "update_subscriber",
                        "list_groups",
                        "get_group",
                        "list_campaigns",
                        "get_campaign",
                    ],
                    required=True,
                ),
                FormField(
                    name="subscriber_id", label="Subscriber ID", placeholder="123"
                ),
                FormField(
                    name="email", label="Email", placeholder="user@example.com"
                ),
                FormField(
                    name="fields",
                    label="Custom Fields (JSON)",
                    field_type="textarea",
                    placeholder='{"name": "John", "last_name": "Doe"}',
                ),
                FormField(name="group_id", label="Group ID", placeholder="123"),
                FormField(name="campaign_id", label="Campaign ID", placeholder="123"),
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
                {"title": "List subscribers", "code": 'operation: "list_subscribers"'},
                {
                    "title": "Create subscriber",
                    "code": 'operation: "create_subscriber"\nemail: "user@example.com"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_subscribers",
        "get_subscriber",
        "create_subscriber",
        "update_subscriber",
        "list_groups",
        "get_group",
        "list_campaigns",
        "get_campaign",
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

    if operation == "list_subscribers":
        url = f"{API_BASE_URL}/subscribers"
    elif operation == "get_subscriber":
        if not subscriber_id:
            return error_response(
                "subscriber_id is required for get_subscriber operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/subscribers/{subscriber_id}"
    elif operation == "create_subscriber":
        if not email:
            return error_response(
                "email is required for create_subscriber operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/subscribers"
        payload = {"email": email}
        if fields:
            import json

            try:
                custom_fields = json.loads(fields)
                payload["fields"] = custom_fields
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON in fields parameter", error_type="validation_error"
                )
    elif operation == "update_subscriber":
        if not subscriber_id:
            return error_response(
                "subscriber_id is required for update_subscriber operation",
                error_type="validation_error",
            )
        method = "PUT"
        url = f"{API_BASE_URL}/subscribers/{subscriber_id}"
        payload = {}
        if email:
            payload["email"] = email
        if fields:
            import json

            try:
                custom_fields = json.loads(fields)
                payload["fields"] = custom_fields
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON in fields parameter", error_type="validation_error"
                )
    elif operation == "list_groups":
        url = f"{API_BASE_URL}/groups"
    elif operation == "get_group":
        if not group_id:
            return error_response(
                "group_id is required for get_group operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/groups/{group_id}"
    elif operation == "list_campaigns":
        url = f"{API_BASE_URL}/campaigns"
    elif operation == "get_campaign":
        if not campaign_id:
            return error_response(
                "campaign_id is required for get_campaign operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/campaigns/{campaign_id}"

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
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
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
