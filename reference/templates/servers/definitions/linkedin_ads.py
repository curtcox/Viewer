# ruff: noqa: F821, F706
"""Call the LinkedIn Marketing API for ads management."""

from __future__ import annotations

from typing import Any, Optional

from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    error_response,
    execute_json_request,
    generate_form,
    missing_secret_error,
    validate_and_build_payload,
    FormField,
)


API_BASE_URL = "https://api.linkedin.com/v2"
DOCUMENTATION_URL = "https://docs.microsoft.com/en-us/linkedin/marketing/"


_OPERATIONS = {
    "list_accounts": OperationDefinition(
        payload_builder=lambda count, **_: {
            "method": "GET",
            "url_path": "adAccounts",
            "params": {"q": "search", "count": count},
            "payload": None,
            "account_id": None,
            "campaign_id": None,
            "campaign_group_id": None,
        },
    ),
    "get_account": OperationDefinition(
        required=(RequiredField("account_id"),),
        payload_builder=lambda account_id, **_: {
            "method": "GET",
            "url_path": f"adAccounts/{account_id.split(':')[-1]}",
            "params": None,
            "payload": None,
            "account_id": account_id,
            "campaign_id": None,
            "campaign_group_id": None,
        },
    ),
    "list_campaigns": OperationDefinition(
        required=(RequiredField("account_id"),),
        payload_builder=lambda account_id, count, **_: {
            "method": "GET",
            "url_path": "adCampaigns",
            "params": {
                "q": "search",
                "search.account.values[0]": account_id,
                "count": count,
            },
            "payload": None,
            "account_id": account_id,
            "campaign_id": None,
            "campaign_group_id": None,
        },
    ),
    "get_campaign": OperationDefinition(
        required=(RequiredField("campaign_id"),),
        payload_builder=lambda campaign_id, **_: {
            "method": "GET",
            "url_path": f"adCampaigns/{campaign_id}",
            "params": None,
            "payload": None,
            "account_id": None,
            "campaign_id": campaign_id,
            "campaign_group_id": None,
        },
    ),
    "create_campaign": OperationDefinition(
        required=(
            RequiredField("account_id"),
            RequiredField("name"),
            RequiredField("campaign_group_id"),
        ),
        payload_builder=lambda account_id, name, campaign_group_id, campaign_type, status, start_date, end_date, **_: {
            "method": "POST",
            "url_path": "adCampaigns",
            "params": None,
            "payload": {
                "account": account_id,
                "name": name,
                "type": campaign_type,
                "status": status,
                "campaignGroup": f"urn:li:sponsoredCampaignGroup:{campaign_group_id}",
                **({} if not start_date else {
                    "runSchedule": {
                        "start": start_date,
                        **({} if not end_date else {"end": end_date}),
                    }
                }),
            },
            "account_id": account_id,
            "campaign_id": None,
            "campaign_group_id": campaign_group_id,
        },
    ),
    "list_campaign_groups": OperationDefinition(
        required=(RequiredField("account_id"),),
        payload_builder=lambda account_id, count, **_: {
            "method": "GET",
            "url_path": "adCampaignGroups",
            "params": {
                "q": "search",
                "search.account.values[0]": account_id,
                "count": count,
            },
            "payload": None,
            "account_id": account_id,
            "campaign_id": None,
            "campaign_group_id": None,
        },
    ),
    "get_campaign_group": OperationDefinition(
        required=(RequiredField("campaign_group_id"),),
        payload_builder=lambda campaign_group_id, **_: {
            "method": "GET",
            "url_path": f"adCampaignGroups/{campaign_group_id}",
            "params": None,
            "payload": None,
            "account_id": None,
            "campaign_id": None,
            "campaign_group_id": campaign_group_id,
        },
    ),
    "get_analytics": OperationDefinition(
        required=(RequiredField("campaign_id"),),
        payload_builder=lambda campaign_id, **_: {
            "method": "GET",
            "url_path": "adAnalytics",
            "params": {
                "q": "analytics",
                "campaigns[0]": f"urn:li:sponsoredCampaign:{campaign_id}",
            },
            "payload": None,
            "account_id": None,
            "campaign_id": campaign_id,
            "campaign_group_id": None,
        },
    ),
}


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
    if operation not in _OPERATIONS:
        valid_ops = list(_OPERATIONS.keys())
        return error_response(
            f"Invalid operation: {operation}. Must be one of: {', '.join(valid_ops)}",
            error_type="validation_error",
        )

    # Validate and build request configuration
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        account_id=account_id,
        campaign_id=campaign_id,
        campaign_group_id=campaign_group_id,
        name=name,
        campaign_type=campaign_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        count=count,
    )
    if isinstance(result, tuple):
        return error_response(result[0], error_type="validation_error")

    # Extract request configuration
    method = result["method"]
    url_path = result["url_path"]
    params = result["params"]
    payload = result["payload"]

    # Build URL
    url = f"{API_BASE_URL}/{url_path}"

    # Dry run: return preview
    if dry_run:
        preview: dict[str, Any] = {
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

    # Build headers
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Accept": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

    # Execute request
    return execute_json_request(
        client,
        method,
        url,
        headers=headers,
        json=payload,
        params=params,
        timeout=timeout,
    )
