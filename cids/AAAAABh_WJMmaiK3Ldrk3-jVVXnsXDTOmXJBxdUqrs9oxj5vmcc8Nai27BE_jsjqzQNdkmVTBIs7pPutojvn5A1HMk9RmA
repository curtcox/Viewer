# ruff: noqa: F821, F706
"""Interact with Google Ads API for campaign management and reporting."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/adwords",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_OPERATIONS = {
    "search": OperationDefinition(
        required=(RequiredField("query", "query is required for search operation"),),
        payload_builder=lambda query, **_: {"query": query},
    ),
    "get_campaign": OperationDefinition(
        required=(
            RequiredField(
                "campaign_id", "campaign_id is required for get_campaign operation"
            ),
        ),
    ),
    "list_campaigns": OperationDefinition(
        payload_builder=lambda **_: {
            "query": "SELECT campaign.id, campaign.name, campaign.status FROM campaign"
        }
    ),
}

_ENDPOINT_BUILDERS = {
    "search": lambda base_url, **_: f"{base_url}/googleAds:search",
    "get_campaign": lambda base_url, campaign_id, **_: f"{base_url}/campaigns/{campaign_id}",
    "list_campaigns": lambda base_url, **_: f"{base_url}/googleAds:search",
}

_METHODS = {
    "search": "POST",
    "list_campaigns": "POST",
    "get_campaign": "GET",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "google_service_account",
    }

    if payload:
        preview["payload"] = payload

    return preview


def _google_ads_error_message(_response: object, data: object) -> str:
    if isinstance(data, dict):
        error = data.get("error", {})
        if isinstance(error, dict):
            return error.get("message", "Google Ads API error")
    return "Google Ads API error"


def main(
    *,
    operation: str = "list_campaigns",
    customer_id: Optional[str] = None,
    query: Optional[str] = None,
    campaign_id: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Ads API.

    Args:
        operation: Operation to perform (search, get_campaign, list_campaigns).
        customer_id: Google Ads customer ID (required for all operations).
        query: GAQL query string (required for search operation).
        campaign_id: Campaign ID (required for get_campaign).
        GOOGLE_SERVICE_ACCOUNT_JSON: Google service account JSON string.
        GOOGLE_ACCESS_TOKEN: Google OAuth access token (alternative to service account).
        GOOGLE_ADS_DEVELOPER_TOKEN: Google Ads developer token (required).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional custom HTTP client (for testing).
        auth_manager: Optional custom auth manager (for testing).
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or preview.
    """
    api_client = client or _DEFAULT_CLIENT
    auth_mgr = auth_manager or _DEFAULT_AUTH_MANAGER

    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN:
        return error_output(
            "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN",
            status_code=401,
            details="Provide either a service account JSON or an access token.",
        )

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        return error_output(
            "Missing GOOGLE_ADS_DEVELOPER_TOKEN",
            status_code=401,
            details="Google Ads developer token is required.",
        )

    if operation not in _OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_OPERATIONS)}"
        )

    if not customer_id:
        return validation_error("customer_id is required")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        query=query,
        campaign_id=campaign_id,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    base_url = f"https://googleads.googleapis.com/v16/customers/{customer_id}"
    url = _ENDPOINT_BUILDERS[operation](
        base_url=base_url,
        campaign_id=campaign_id,
    )
    method = _METHODS.get(operation, "GET")

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Get access token
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            return error_output(
                "Invalid GOOGLE_SERVICE_ACCOUNT_JSON format",
                status_code=400,
                details="Service account JSON must be valid JSON.",
            )

        token_response = auth_mgr.get_access_token(
            service_account_info=service_account_info,
            scopes=_SCOPES,
        )
        if "error" in token_response.get("output", {}):
            return token_response

        access_token = token_response["access_token"]
    else:
        access_token = GOOGLE_ACCESS_TOKEN

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_google_ads_error_message,
        request_error_message="Google Ads request failed",
    )
