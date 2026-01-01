# ruff: noqa: F821, F706
"""Call the Klaviyo API for email marketing and customer data."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://a.klaviyo.com/api"
DOCUMENTATION_URL = "https://developers.klaviyo.com/en/reference/api-overview"


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
    valid_operations = [
        "list_profiles",
        "get_profile",
        "create_profile",
        "list_lists",
        "get_list",
        "create_list",
        "add_profile_to_list",
        "get_events",
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

    if operation == "list_profiles":
        url = f"{API_BASE_URL}/profiles"
    elif operation == "get_profile":
        if not profile_id:
            return error_response(
                "profile_id is required for get_profile operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/profiles/{profile_id}"
    elif operation == "create_profile":
        if not email:
            return error_response(
                "email is required for create_profile operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/profiles"
        payload = {
            "data": {
                "type": "profile",
                "attributes": {
                    "email": email,
                },
            }
        }
        if first_name:
            payload["data"]["attributes"]["first_name"] = first_name
        if last_name:
            payload["data"]["attributes"]["last_name"] = last_name
        if phone_number:
            payload["data"]["attributes"]["phone_number"] = phone_number
        if properties:
            import json

            try:
                props = json.loads(properties)
                payload["data"]["attributes"]["properties"] = props
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON in properties field", error_type="validation_error"
                )
    elif operation == "list_lists":
        url = f"{API_BASE_URL}/lists"
    elif operation == "get_list":
        if not list_id:
            return error_response(
                "list_id is required for get_list operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/lists/{list_id}"
    elif operation == "create_list":
        if not list_id:
            return error_response(
                "list_id is required for create_list operation (used as name)",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/lists"
        payload = {"data": {"type": "list", "attributes": {"name": list_id}}}
    elif operation == "add_profile_to_list":
        if not list_id or not profile_id:
            return error_response(
                "list_id and profile_id are required for add_profile_to_list operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/lists/{list_id}/relationships/profiles"
        payload = {"data": [{"type": "profile", "id": profile_id}]}
    elif operation == "get_events":
        url = f"{API_BASE_URL}/events"

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

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "Accept": "application/json",
        "revision": "2024-10-15",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

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
