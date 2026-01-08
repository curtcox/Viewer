# ruff: noqa: F821, F706
"""Call the Klaviyo API for email marketing and customer data."""

import json
from typing import Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    missing_secret_error,
    generate_form,
    FormField,
    validate_and_build_payload,
    validation_error,
)


API_BASE_URL = "https://a.klaviyo.com/api"
DOCUMENTATION_URL = "https://developers.klaviyo.com/en/reference/api-overview"

_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_profiles": OperationDefinition(),
    "get_profile": OperationDefinition(
        required=(RequiredField("profile_id"),),
    ),
    "create_profile": OperationDefinition(
        required=(RequiredField("email"),),
        payload_builder=lambda email, first_name, last_name, phone_number, properties, **_: {
            "data": {
                "type": "profile",
                "attributes": {
                    "email": email,
                    **({"first_name": first_name} if first_name else {}),
                    **({"last_name": last_name} if last_name else {}),
                    **({"phone_number": phone_number} if phone_number else {}),
                    **({"properties": properties} if properties else {}),
                },
            },
        },
    ),
    "list_lists": OperationDefinition(),
    "get_list": OperationDefinition(
        required=(RequiredField("list_id"),),
    ),
    "create_list": OperationDefinition(
        required=(RequiredField("list_id"),),
        payload_builder=lambda list_id, **_: {
            "data": {"type": "list", "attributes": {"name": list_id}},
        },
    ),
    "add_profile_to_list": OperationDefinition(
        required=(RequiredField("list_id"), RequiredField("profile_id")),
        payload_builder=lambda list_id, profile_id, **_: {
            "data": [{"type": "profile", "id": profile_id}],
        },
    ),
    "get_events": OperationDefinition(),
}

_ENDPOINT_BUILDERS = {
    "list_profiles": lambda **_: "profiles",
    "get_profile": lambda profile_id, **_: f"profiles/{profile_id}",
    "create_profile": lambda **_: "profiles",
    "list_lists": lambda **_: "lists",
    "get_list": lambda list_id, **_: f"lists/{list_id}",
    "create_list": lambda **_: "lists",
    "add_profile_to_list": lambda list_id, **_: f"lists/{list_id}/relationships/profiles",
    "get_events": lambda **_: "events",
}

_METHODS = {
    "create_profile": "POST",
    "create_list": "POST",
    "add_profile_to_list": "POST",
}


def _klaviyo_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        errors = data.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                return (
                    first.get("detail")
                    or first.get("title")
                    or first.get("code")
                    or "Klaviyo API error"
                )
            return str(first)
        return data.get("message") or "Klaviyo API error"
    return "Klaviyo API error"


def main(
    operation: str = "",
    profile_id: str = "",
    list_id: str = "",
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    phone_number: str = "",
    properties: Optional[str] = None,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    KLAVIYO_API_KEY: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Klaviyo API.

    Args:
        operation: Operation to perform (list_profiles, get_profile, create_profile,
                   list_lists, get_list, create_list, add_profile_to_list, get_events)
        profile_id: Profile ID for profile operations
        list_id: List ID for list operations
        email: Email address for profile creation
        first_name: First name for profile creation
        last_name: Last name for profile creation
        phone_number: Phone number for profile creation
        properties: JSON string of additional properties
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        KLAVIYO_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not KLAVIYO_API_KEY:
        return missing_secret_error("KLAVIYO_API_KEY")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="klaviyo",
            title="Klaviyo API",
            description="Access Klaviyo email marketing and customer data platform.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_profiles",
                        "get_profile",
                        "create_profile",
                        "list_lists",
                        "get_list",
                        "create_list",
                        "add_profile_to_list",
                        "get_events",
                    ],
                    required=True,
                ),
                FormField(
                    name="profile_id", label="Profile ID", placeholder="01ABCDEF..."
                ),
                FormField(name="list_id", label="List ID", placeholder="XyZ123"),
                FormField(
                    name="email", label="Email", placeholder="user@example.com"
                ),
                FormField(name="first_name", label="First Name", placeholder="John"),
                FormField(name="last_name", label="Last Name", placeholder="Doe"),
                FormField(
                    name="phone_number", label="Phone Number", placeholder="+1234567890"
                ),
                FormField(
                    name="properties",
                    label="Additional Properties (JSON)",
                    field_type="textarea",
                    placeholder='{"custom_field": "value"}',
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
                    "title": "List profiles",
                    "code": 'operation: "list_profiles"',
                },
                {
                    "title": "Create profile",
                    "code": 'operation: "create_profile"\nemail: "user@example.com"\nfirst_name: "John"',
                },
                {
                    "title": "Get profile",
                    "code": 'operation: "get_profile"\nprofile_id: "01ABCDEF..."',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    parsed_properties = None
    if properties:
        try:
            parsed_properties = json.loads(properties) if isinstance(properties, str) else properties
        except json.JSONDecodeError:
            return validation_error("Invalid JSON in properties field", field="properties")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        profile_id=profile_id,
        list_id=list_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        properties=parsed_properties,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    endpoint = _ENDPOINT_BUILDERS[operation](profile_id=profile_id, list_id=list_id)
    url = f"{API_BASE_URL}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Klaviyo-API-Key [REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    api_client = client or _DEFAULT_CLIENT

    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "Accept": "application/json",
        "revision": "2024-10-15",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_klaviyo_error_message,
        request_error_message="Klaviyo request failed",
    )
