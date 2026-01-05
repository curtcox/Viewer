# ruff: noqa: F821, F706
"""Call the ActiveCampaign API for marketing automation and CRM."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


DOCUMENTATION_URL = "https://developers.activecampaign.com/reference"


def main(
    operation: str = "",
    contact_id: str = "",
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    list_id: str = "",
    campaign_id: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    *,
    ACTIVECAMPAIGN_API_KEY: str,
    ACTIVECAMPAIGN_URL: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the ActiveCampaign API.

    Args:
        operation: Operation to perform (list_contacts, get_contact, create_contact,
                   update_contact, list_lists, get_list, list_campaigns, get_campaign)
        contact_id: Contact ID for contact operations
        email: Email address for contact creation
        first_name: First name for contact
        last_name: Last name for contact
        list_id: List ID for list operations
        campaign_id: Campaign ID for campaign operations
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        ACTIVECAMPAIGN_API_KEY: API key for authentication (from secrets)
        ACTIVECAMPAIGN_URL: ActiveCampaign account URL (e.g., https://youraccountname.api-us1.com)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secrets first
    if not ACTIVECAMPAIGN_API_KEY:
        return missing_secret_error("ACTIVECAMPAIGN_API_KEY")
    if not ACTIVECAMPAIGN_URL:
        return missing_secret_error("ACTIVECAMPAIGN_URL")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="activecampaign",
            title="ActiveCampaign API",
            description="Access ActiveCampaign marketing automation and CRM platform.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_contacts",
                        "get_contact",
                        "create_contact",
                        "update_contact",
                        "list_lists",
                        "get_list",
                        "list_campaigns",
                        "get_campaign",
                    ],
                    required=True,
                ),
                FormField(name="contact_id", label="Contact ID", placeholder="123"),
                FormField(
                    name="email", label="Email", placeholder="user@example.com"
                ),
                FormField(name="first_name", label="First Name", placeholder="John"),
                FormField(name="last_name", label="Last Name", placeholder="Doe"),
                FormField(name="list_id", label="List ID", placeholder="1"),
                FormField(name="campaign_id", label="Campaign ID", placeholder="1"),
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
                {"title": "List contacts", "code": 'operation: "list_contacts"'},
                {
                    "title": "Create contact",
                    "code": 'operation: "create_contact"\nemail: "user@example.com"\nfirst_name: "John"',
                },
                {
                    "title": "Get contact",
                    "code": 'operation: "get_contact"\ncontact_id: "123"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_contacts",
        "get_contact",
        "create_contact",
        "update_contact",
        "list_lists",
        "get_list",
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
    url = ACTIVECAMPAIGN_URL.rstrip("/")
    payload = None

    if operation == "list_contacts":
        url = f"{url}/api/3/contacts"
    elif operation == "get_contact":
        if not contact_id:
            return error_response(
                "contact_id is required for get_contact operation",
                error_type="validation_error",
            )
        url = f"{url}/api/3/contacts/{contact_id}"
    elif operation == "create_contact":
        if not email:
            return error_response(
                "email is required for create_contact operation",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{url}/api/3/contacts"
        payload = {"contact": {"email": email}}
        if first_name:
            payload["contact"]["firstName"] = first_name
        if last_name:
            payload["contact"]["lastName"] = last_name
    elif operation == "update_contact":
        if not contact_id:
            return error_response(
                "contact_id is required for update_contact operation",
                error_type="validation_error",
            )
        method = "PUT"
        url = f"{url}/api/3/contacts/{contact_id}"
        payload = {"contact": {}}
        if email:
            payload["contact"]["email"] = email
        if first_name:
            payload["contact"]["firstName"] = first_name
        if last_name:
            payload["contact"]["lastName"] = last_name
    elif operation == "list_lists":
        url = f"{url}/api/3/lists"
    elif operation == "get_list":
        if not list_id:
            return error_response(
                "list_id is required for get_list operation",
                error_type="validation_error",
            )
        url = f"{url}/api/3/lists/{list_id}"
    elif operation == "list_campaigns":
        url = f"{url}/api/3/campaigns"
    elif operation == "get_campaign":
        if not campaign_id:
            return error_response(
                "campaign_id is required for get_campaign operation",
                error_type="validation_error",
            )
        url = f"{url}/api/3/campaigns/{campaign_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Api-Token": "[REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Api-Token": ACTIVECAMPAIGN_API_KEY,
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
