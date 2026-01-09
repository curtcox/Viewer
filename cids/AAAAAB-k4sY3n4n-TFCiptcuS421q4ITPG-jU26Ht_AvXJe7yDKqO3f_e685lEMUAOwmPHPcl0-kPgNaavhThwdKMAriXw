# ruff: noqa: F821, F706
"""Call the MailerLite API for email marketing."""

from typing import Any, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    generate_form,
    FormField,
    missing_secret_error,
    validate_and_build_payload,
    validation_error,
)


API_BASE_URL = "https://connect.mailerlite.com/api"
DOCUMENTATION_URL = "https://developers.mailerlite.com/docs"

_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_subscribers": OperationDefinition(),
    "get_subscriber": OperationDefinition(
        required=(
            RequiredField("subscriber_id", "subscriber_id is required for get_subscriber operation"),
        ),
    ),
    "create_subscriber": OperationDefinition(
        required=(RequiredField("email", "email is required for create_subscriber operation"),),
        payload_builder=lambda email, fields, **_: {"email": email, **({"fields": fields} if fields else {})},
    ),
    "update_subscriber": OperationDefinition(
        required=(
            RequiredField("subscriber_id", "subscriber_id is required for update_subscriber operation"),
        ),
        payload_builder=lambda email, fields, **_: {
            **({"email": email} if email else {}),
            **({"fields": fields} if fields else {}),
        },
    ),
    "list_groups": OperationDefinition(),
    "get_group": OperationDefinition(
        required=(RequiredField("group_id", "group_id is required for get_group operation"),),
    ),
    "list_campaigns": OperationDefinition(),
    "get_campaign": OperationDefinition(
        required=(RequiredField("campaign_id", "campaign_id is required for get_campaign operation"),),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_subscribers": lambda **_: f"{API_BASE_URL}/subscribers",
    "get_subscriber": lambda subscriber_id, **_: f"{API_BASE_URL}/subscribers/{subscriber_id}",
    "create_subscriber": lambda **_: f"{API_BASE_URL}/subscribers",
    "update_subscriber": lambda subscriber_id, **_: f"{API_BASE_URL}/subscribers/{subscriber_id}",
    "list_groups": lambda **_: f"{API_BASE_URL}/groups",
    "get_group": lambda group_id, **_: f"{API_BASE_URL}/groups/{group_id}",
    "list_campaigns": lambda **_: f"{API_BASE_URL}/campaigns",
    "get_campaign": lambda campaign_id, **_: f"{API_BASE_URL}/campaigns/{campaign_id}",
}

_METHODS = {
    "create_subscriber": "POST",
    "update_subscriber": "PUT",
}


def _parse_fields(fields: Optional[str]) -> dict[str, Any] | None | tuple[str, str]:
    if not fields:
        return None
    try:
        import json

        return json.loads(fields)
    except json.JSONDecodeError:
        return ("Invalid JSON in fields parameter", "fields")


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

    if operation not in _OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Must be one of: {', '.join(_OPERATIONS)}",
            field="operation",
        )

    parsed_fields = _parse_fields(fields)
    if isinstance(parsed_fields, tuple):
        return validation_error(parsed_fields[0], field=parsed_fields[1])

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        subscriber_id=subscriber_id,
        email=email,
        fields=parsed_fields,
        group_id=group_id,
        campaign_id=campaign_id,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    url = _ENDPOINT_BUILDERS[operation](
        subscriber_id=subscriber_id,
        group_id=group_id,
        campaign_id=campaign_id,
    )
    method = _METHODS.get(operation, "GET")

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

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        request_error_message="MailerLite request failed",
    )
