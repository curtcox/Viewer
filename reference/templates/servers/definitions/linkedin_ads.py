# ruff: noqa: F821, F706
"""Call the LinkedIn Marketing API for ads management."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.linkedin.com/v2"
DOCUMENTATION_URL = "https://docs.microsoft.com/en-us/linkedin/marketing/"


def main(
    operation: str = "",
    account_id: str = "",
    campaign_id: str = "",
    campaign_group_id: str = "",
    name: str = "",
    campaign_type: str = "TEXT_AD",
    status: str = "PAUSED",
    start_date: str = "",
    end_date: str = "",
    count: int = 10,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    LINKEDIN_ACCESS_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the LinkedIn Marketing API.

    Args:
        operation: Operation to perform (list_accounts, get_account, list_campaigns,
                   get_campaign, create_campaign, list_campaign_groups, get_campaign_group,
                   get_analytics)
        account_id: Ad account ID (format: urn:li:sponsoredAccount:123456)
        campaign_id: Campaign ID for campaign operations
        campaign_group_id: Campaign group ID for group operations
        name: Name for campaign creation
        campaign_type: Campaign type (TEXT_AD, SPONSORED_UPDATES, SPONSORED_INMAILS)
        status: Campaign status (ACTIVE, PAUSED, ARCHIVED, COMPLETED, CANCELED, DRAFT)
        start_date: Campaign start date (ISO 8601 format)
        end_date: Campaign end date (ISO 8601 format)
        count: Maximum number of results to return (default: 10)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        LINKEDIN_ACCESS_TOKEN: Access token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not LINKEDIN_ACCESS_TOKEN:
        return missing_secret_error("LINKEDIN_ACCESS_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="linkedin_ads",
            title="LinkedIn Marketing API",
            description="Access LinkedIn Marketing API for ads and campaigns management.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_accounts",
                        "get_account",
                        "list_campaigns",
                        "get_campaign",
                        "create_campaign",
                        "list_campaign_groups",
                        "get_campaign_group",
                        "get_analytics",
                    ],
                    required=True,
                ),
                FormField(
                    name="account_id",
                    label="Ad Account ID",
                    placeholder="urn:li:sponsoredAccount:123456",
                    help_text="Required for most operations",
                ),
                FormField(
                    name="campaign_id",
                    label="Campaign ID",
                    placeholder="123456789",
                ),
                FormField(
                    name="campaign_group_id",
                    label="Campaign Group ID",
                    placeholder="987654321",
                ),
                FormField(
                    name="name",
                    label="Name",
                    placeholder="My Campaign",
                    help_text="Required for create_campaign",
                ),
                FormField(
                    name="campaign_type",
                    label="Campaign Type",
                    field_type="select",
                    options=["TEXT_AD", "SPONSORED_UPDATES", "SPONSORED_INMAILS"],
                    default="TEXT_AD",
                ),
                FormField(
                    name="status",
                    label="Status",
                    field_type="select",
                    options=["ACTIVE", "PAUSED", "ARCHIVED", "COMPLETED", "CANCELED", "DRAFT"],
                    default="PAUSED",
                ),
                FormField(
                    name="start_date",
                    label="Start Date",
                    placeholder="2024-01-01",
                    help_text="ISO 8601 format",
                ),
                FormField(
                    name="end_date",
                    label="End Date",
                    placeholder="2024-12-31",
                    help_text="ISO 8601 format",
                ),
                FormField(
                    name="count", label="Count", default="10", help_text="Max results"
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
                    "title": "List ad accounts",
                    "code": 'operation: "list_accounts"',
                },
                {
                    "title": "List campaigns",
                    "code": 'operation: "list_campaigns"\naccount_id: "urn:li:sponsoredAccount:123456"',
                },
                {
                    "title": "Get campaign",
                    "code": 'operation: "get_campaign"\ncampaign_id: "123456789"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_accounts",
        "get_account",
        "list_campaigns",
        "get_campaign",
        "create_campaign",
        "list_campaign_groups",
        "get_campaign_group",
        "get_analytics",
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
    params = {}

    if operation == "list_accounts":
        url = f"{API_BASE_URL}/adAccounts"
        params["q"] = "search"
        params["count"] = count
    elif operation == "get_account":
        if not account_id:
            return error_response(
                "account_id is required for get_account operation",
                error_type="validation_error",
            )
        # Extract the numeric ID from URN format
        numeric_id = account_id.split(":")[-1]
        url = f"{API_BASE_URL}/adAccounts/{numeric_id}"
    elif operation == "list_campaigns":
        if not account_id:
            return error_response(
                "account_id is required for list_campaigns operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/adCampaigns"
        params["q"] = "search"
        params["search.account.values[0]"] = account_id
        params["count"] = count
    elif operation == "get_campaign":
        if not campaign_id:
            return error_response(
                "campaign_id is required for get_campaign operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/adCampaigns/{campaign_id}"
    elif operation == "create_campaign":
        if not account_id or not name or not campaign_group_id:
            return error_response(
                "account_id, name, and campaign_group_id are required for create_campaign",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/adCampaigns"
        payload = {
            "account": account_id,
            "name": name,
            "type": campaign_type,
            "status": status,
            "campaignGroup": f"urn:li:sponsoredCampaignGroup:{campaign_group_id}",
        }
        if start_date:
            payload["runSchedule"] = {"start": start_date}
            if end_date:
                payload["runSchedule"]["end"] = end_date
    elif operation == "list_campaign_groups":
        if not account_id:
            return error_response(
                "account_id is required for list_campaign_groups operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/adCampaignGroups"
        params["q"] = "search"
        params["search.account.values[0]"] = account_id
        params["count"] = count
    elif operation == "get_campaign_group":
        if not campaign_group_id:
            return error_response(
                "campaign_group_id is required for get_campaign_group operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/adCampaignGroups/{campaign_group_id}"
    elif operation == "get_analytics":
        if not campaign_id:
            return error_response(
                "campaign_id is required for get_analytics operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/adAnalytics"
        params["q"] = "analytics"
        params["campaigns[0]"] = f"urn:li:sponsoredCampaign:{campaign_id}"

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "headers": {"Authorization": "Bearer [REDACTED]"},
        }
        if params:
            preview["params"] = params
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Accept": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if payload else None,
            params=params if params else None,
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
