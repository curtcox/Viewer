# ruff: noqa: F821, F706
"""Call the Meta (Facebook) Marketing API for ads management."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://graph.facebook.com/v18.0"
DOCUMENTATION_URL = "https://developers.facebook.com/docs/marketing-apis"


def main(
    operation: str = "",
    account_id: str = "",
    campaign_id: str = "",
    ad_set_id: str = "",
    ad_id: str = "",
    campaign_name: str = "",
    objective: str = "",
    status: str = "PAUSED",
    fields: str = "",
    limit: int = 25,
    timeout: int = 60,
    dry_run: bool = True,
    *,
    META_ACCESS_TOKEN: str,
    context=None,
    client: Optional[ExternalApiClient] = None,
):
    """
    Make a request to the Meta Marketing API.

    Args:
        operation: Operation to perform (list_accounts, list_campaigns, get_campaign,
                   create_campaign, list_adsets, get_adset, list_ads, get_ad, get_insights)
        account_id: Ad account ID (format: act_123456789)
        campaign_id: Campaign ID for campaign operations
        ad_set_id: Ad set ID for ad set operations
        ad_id: Ad ID for ad operations
        campaign_name: Campaign name for creation
        objective: Campaign objective for creation (e.g., OUTCOME_TRAFFIC, OUTCOME_AWARENESS)
        status: Campaign/AdSet/Ad status (ACTIVE, PAUSED, DELETED, ARCHIVED)
        fields: Comma-separated list of fields to retrieve
        limit: Maximum number of results to return (default: 25)
        timeout: Request timeout in seconds (default: 60)
        dry_run: If True, return preview without making actual API call (default: True)
        META_ACCESS_TOKEN: Access token for authentication (from secrets)
        context: Request context (optional)
        client: ExternalApiClient instance (optional, for testing)

    Returns:
        Dict with 'output' containing the API response or preview
    """
    # Validate secret first
    if not META_ACCESS_TOKEN:
        return missing_secret_error("META_ACCESS_TOKEN")

    # Show form if no operation provided
    if not operation:
        return generate_form(
            server_name="meta_ads",
            title="Meta (Facebook) Marketing API",
            description="Access Meta Marketing API for ads and campaigns management.",
            fields=[
                FormField(
                    name="operation",
                    label="Operation",
                    field_type="select",
                    options=[
                        "list_accounts",
                        "list_campaigns",
                        "get_campaign",
                        "create_campaign",
                        "list_adsets",
                        "get_adset",
                        "list_ads",
                        "get_ad",
                        "get_insights",
                    ],
                    required=True,
                ),
                FormField(
                    name="account_id",
                    label="Ad Account ID",
                    placeholder="act_123456789",
                    help_text="Required for most operations",
                ),
                FormField(
                    name="campaign_id", label="Campaign ID", placeholder="120123456789"
                ),
                FormField(name="ad_set_id", label="Ad Set ID", placeholder="120123456790"),
                FormField(name="ad_id", label="Ad ID", placeholder="120123456791"),
                FormField(
                    name="campaign_name",
                    label="Campaign Name",
                    placeholder="My Campaign",
                    help_text="Required for create_campaign",
                ),
                FormField(
                    name="objective",
                    label="Campaign Objective",
                    placeholder="OUTCOME_TRAFFIC",
                    help_text="Required for create_campaign",
                ),
                FormField(
                    name="status",
                    label="Status",
                    field_type="select",
                    options=["ACTIVE", "PAUSED", "DELETED", "ARCHIVED"],
                    default="PAUSED",
                ),
                FormField(
                    name="fields",
                    label="Fields",
                    placeholder="name,status,objective",
                    help_text="Comma-separated list of fields",
                ),
                FormField(
                    name="limit", label="Limit", default="25", help_text="Max results"
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
                    "code": 'operation: "list_campaigns"\naccount_id: "act_123456789"',
                },
                {
                    "title": "Get campaign details",
                    "code": 'operation: "get_campaign"\ncampaign_id: "120123456789"',
                },
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate operation
    valid_operations = [
        "list_accounts",
        "list_campaigns",
        "get_campaign",
        "create_campaign",
        "list_adsets",
        "get_adset",
        "list_ads",
        "get_ad",
        "get_insights",
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
    params = {"access_token": META_ACCESS_TOKEN}

    if operation == "list_accounts":
        url = f"{API_BASE_URL}/me/adaccounts"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif operation == "list_campaigns":
        if not account_id:
            return error_response(
                "account_id is required for list_campaigns operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{account_id}/campaigns"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif operation == "get_campaign":
        if not campaign_id:
            return error_response(
                "campaign_id is required for get_campaign operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{campaign_id}"
        if fields:
            params["fields"] = fields
    elif operation == "create_campaign":
        if not account_id or not campaign_name or not objective:
            return error_response(
                "account_id, campaign_name, and objective are required for create_campaign",
                error_type="validation_error",
            )
        method = "POST"
        url = f"{API_BASE_URL}/{account_id}/campaigns"
        payload = {
            "name": campaign_name,
            "objective": objective,
            "status": status,
            "special_ad_categories": "[]",
        }
    elif operation == "list_adsets":
        if not account_id:
            return error_response(
                "account_id is required for list_adsets operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{account_id}/adsets"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif operation == "get_adset":
        if not ad_set_id:
            return error_response(
                "ad_set_id is required for get_adset operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{ad_set_id}"
        if fields:
            params["fields"] = fields
    elif operation == "list_ads":
        if not account_id:
            return error_response(
                "account_id is required for list_ads operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{account_id}/ads"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif operation == "get_ad":
        if not ad_id:
            return error_response(
                "ad_id is required for get_ad operation",
                error_type="validation_error",
            )
        url = f"{API_BASE_URL}/{ad_id}"
        if fields:
            params["fields"] = fields
    elif operation == "get_insights":
        if not campaign_id and not ad_set_id and not ad_id:
            return error_response(
                "campaign_id, ad_set_id, or ad_id is required for get_insights",
                error_type="validation_error",
            )
        entity_id = campaign_id or ad_set_id or ad_id
        url = f"{API_BASE_URL}/{entity_id}/insights"
        if fields:
            params["fields"] = fields

    # Dry run: return preview
    if dry_run:
        preview = {
            "operation": operation,
            "method": method,
            "url": url,
            "params": {**params, "access_token": "[REDACTED]"},
        }
        if payload:
            preview["payload"] = payload
        return {"output": preview}

    # Create client with configured timeout
    if client is None:
        config = HttpClientConfig(timeout=timeout)
        client = ExternalApiClient(config)

    headers = {
        "Accept": "application/json",
    }
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"

    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if payload else None,
            params=params,
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
