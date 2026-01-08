# ruff: noqa: F821, F706
"""Call the Meta (Facebook) Marketing API for ads management."""

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    PreviewBuilder,
    RequiredField,
    error_output,
    execute_json_request,
    generate_form,
    validation_error,
    FormField,
    validate_and_build_payload,
)


API_BASE_URL = "https://graph.facebook.com/v18.0"
DOCUMENTATION_URL = "https://developers.facebook.com/docs/marketing-apis"

_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_accounts": OperationDefinition(),
    "list_campaigns": OperationDefinition(
        required=(RequiredField("account_id"),),
    ),
    "get_campaign": OperationDefinition(
        required=(RequiredField("campaign_id"),),
    ),
    "create_campaign": OperationDefinition(
        required=(
            RequiredField("account_id"),
            RequiredField("campaign_name"),
            RequiredField("objective"),
        ),
        payload_builder=lambda campaign_name, objective, status, **_: {
            "name": campaign_name,
            "objective": objective,
            "status": status,
            "special_ad_categories": "[]",
        },
    ),
    "list_adsets": OperationDefinition(
        required=(RequiredField("account_id"),),
    ),
    "get_adset": OperationDefinition(
        required=(RequiredField("ad_set_id"),),
    ),
    "list_ads": OperationDefinition(
        required=(RequiredField("account_id"),),
    ),
    "get_ad": OperationDefinition(
        required=(RequiredField("ad_id"),),
    ),
    "get_insights": OperationDefinition(),
}

_ENDPOINT_BUILDERS = {
    "list_accounts": lambda **_: "me/adaccounts",
    "list_campaigns": lambda account_id, **_: f"{account_id}/campaigns",
    "get_campaign": lambda campaign_id, **_: f"{campaign_id}",
    "create_campaign": lambda account_id, **_: f"{account_id}/campaigns",
    "list_adsets": lambda account_id, **_: f"{account_id}/adsets",
    "get_adset": lambda ad_set_id, **_: f"{ad_set_id}",
    "list_ads": lambda account_id, **_: f"{account_id}/ads",
    "get_ad": lambda ad_id, **_: f"{ad_id}",
    "get_insights": lambda campaign_id, ad_set_id, ad_id, **_: (
        f"{campaign_id or ad_set_id or ad_id}/insights"
    ),
}

_METHODS = {"create_campaign": "POST"}

_PARAMETER_BUILDERS = {
    "list_accounts": lambda limit, fields, **_: _build_list_params(limit, fields),
    "list_campaigns": lambda limit, fields, **_: _build_list_params(limit, fields),
    "list_adsets": lambda limit, fields, **_: _build_list_params(limit, fields),
    "list_ads": lambda limit, fields, **_: _build_list_params(limit, fields),
    "get_campaign": lambda fields, **_: _build_fields_params(fields),
    "get_adset": lambda fields, **_: _build_fields_params(fields),
    "get_ad": lambda fields, **_: _build_fields_params(fields),
    "get_insights": lambda fields, **_: _build_fields_params(fields),
}


def _build_fields_params(fields: str) -> Dict[str, str]:
    if fields:
        return {"fields": fields}
    return {}


def _build_list_params(limit: int, fields: str) -> Dict[str, str | int]:
    params: Dict[str, str | int] = {"limit": limit}
    if fields:
        params["fields"] = fields
    return params


def _build_preview_params(params: Dict[str, str | int]) -> Dict[str, str | int]:
    preview_params = dict(params)
    preview_params["access_token"] = "[REDACTED]"
    return preview_params


def _meta_error_message(_response, data: Any) -> str:
    if isinstance(data, dict):
        error_info = data.get("error")
        if isinstance(error_info, dict):
            return error_info.get("message", "Meta API error")
    return "Meta API error"


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
) -> Dict[str, Any]:
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
    if not META_ACCESS_TOKEN:
        return error_output("Missing META_ACCESS_TOKEN", status_code=401)

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

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        account_id=account_id,
        campaign_id=campaign_id,
        ad_set_id=ad_set_id,
        ad_id=ad_id,
        campaign_name=campaign_name,
        objective=objective,
        status=status,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    if operation == "get_insights" and not (campaign_id or ad_set_id or ad_id):
        return validation_error(
            "campaign_id, ad_set_id, or ad_id is required for get_insights",
        )

    endpoint_builder = _ENDPOINT_BUILDERS.get(operation)
    if not endpoint_builder:
        return validation_error("Unsupported operation", field="operation")

    endpoint = endpoint_builder(
        account_id=account_id,
        campaign_id=campaign_id,
        ad_set_id=ad_set_id,
        ad_id=ad_id,
    )
    url = f"{API_BASE_URL}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    payload = result if isinstance(result, dict) else None
    params = _PARAMETER_BUILDERS.get(operation, lambda **_: {})
    params = params(limit=limit, fields=fields)
    params["access_token"] = META_ACCESS_TOKEN

    if dry_run:
        preview = PreviewBuilder.build(
            operation=operation,
            url=url,
            method=method,
            auth_type="Access Token",
            params=_build_preview_params(params),
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    api_client = client or _DEFAULT_CLIENT
    headers = {"Accept": "application/json"}
    if method in {"POST", "PUT", "PATCH"}:
        headers["Content-Type"] = "application/json"

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_meta_error_message,
        request_error_message="Request failed",
        include_exception_in_message=True,
    )
