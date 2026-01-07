# ruff: noqa: F821, F706
"""Call the Meta (Facebook) Marketing API for ads management."""

from typing import Optional
from server_utils.external_api import (
    CredentialValidator,
    ExternalApiClient,
    HttpClientConfig,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
    error_response,
    generate_form,
    FormField,
)


API_BASE_URL = "https://graph.facebook.com/v18.0"
DOCUMENTATION_URL = "https://developers.facebook.com/docs/marketing-apis"

_OPERATIONS = {
    "list_accounts",
    "list_campaigns",
    "get_campaign",
    "create_campaign",
    "list_adsets",
    "get_adset",
    "list_ads",
    "get_ad",
    "get_insights",
}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)

_PARAMETER_REQUIREMENTS = {
    "list_campaigns": ["account_id"],
    "create_campaign": ["account_id", "campaign_name", "objective"],
    "get_campaign": ["campaign_id"],
    "list_adsets": ["account_id"],
    "get_adset": ["ad_set_id"],
    "list_ads": ["account_id"],
    "get_ad": ["ad_id"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


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
    if error := CredentialValidator.require_secret(META_ACCESS_TOKEN, "META_ACCESS_TOKEN"):
        return error

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
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {
            "account_id": account_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "objective": objective,
            "ad_set_id": ad_set_id,
            "ad_id": ad_id,
        },
    ):
        return error

    # Additional validation for get_insights
    if normalized_operation == "get_insights" and not (campaign_id or ad_set_id or ad_id):
        return error_response(
            "campaign_id, ad_set_id, or ad_id is required for get_insights",
            error_type="validation_error",
        )

    # Build request based on operation
    method = "GET"
    payload = None
    params = {"access_token": META_ACCESS_TOKEN}

    if normalized_operation == "list_accounts":
        url = f"{API_BASE_URL}/me/adaccounts"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif normalized_operation == "list_campaigns":
        url = f"{API_BASE_URL}/{account_id}/campaigns"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif normalized_operation == "get_campaign":
        url = f"{API_BASE_URL}/{campaign_id}"
        if fields:
            params["fields"] = fields
    elif normalized_operation == "create_campaign":
        method = "POST"
        url = f"{API_BASE_URL}/{account_id}/campaigns"
        payload = {
            "name": campaign_name,
            "objective": objective,
            "status": status,
            "special_ad_categories": "[]",
        }
    elif normalized_operation == "list_adsets":
        url = f"{API_BASE_URL}/{account_id}/adsets"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif normalized_operation == "get_adset":
        url = f"{API_BASE_URL}/{ad_set_id}"
        if fields:
            params["fields"] = fields
    elif normalized_operation == "list_ads":
        url = f"{API_BASE_URL}/{account_id}/ads"
        params["limit"] = limit
        if fields:
            params["fields"] = fields
    elif normalized_operation == "get_ad":
        url = f"{API_BASE_URL}/{ad_id}"
        if fields:
            params["fields"] = fields
    elif normalized_operation == "get_insights":
        entity_id = campaign_id or ad_set_id or ad_id
        url = f"{API_BASE_URL}/{entity_id}/insights"
        if fields:
            params["fields"] = fields
    else:
        url = API_BASE_URL

    # Dry run: return preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Access Token",
            params={**params, "access_token": "[REDACTED]"},
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

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
    except Exception as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Extract error message from Meta API response
    def extract_error(data):
        if isinstance(data, dict) and "error" in data:
            error_info = data["error"]
            if isinstance(error_info, dict):
                return error_info.get("message", "Meta API error")
        return "Meta API error"

    return ResponseHandler.handle_json_response(response, extract_error)
