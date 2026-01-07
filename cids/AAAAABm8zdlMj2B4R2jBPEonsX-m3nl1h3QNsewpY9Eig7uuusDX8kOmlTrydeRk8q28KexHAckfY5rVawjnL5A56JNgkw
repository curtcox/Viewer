# ruff: noqa: F821, F706
"""Interact with Google Analytics Data API to retrieve reports and metrics."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    GoogleAuthManager,
    error_output,
    validation_error,
)


_SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_SUPPORTED_OPERATIONS = {
    "run_report",
    "run_realtime_report",
    "get_metadata",
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


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )


def main(
    *,
    operation: str = "run_report",
    property_id: Optional[str] = None,
    dimensions: Optional[str] = None,
    metrics: Optional[str] = None,
    date_ranges: Optional[str] = None,
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Analytics Data API.

    Args:
        operation: Operation to perform (run_report, run_realtime_report, get_metadata).
        property_id: GA4 Property ID (required for all operations).
        dimensions: Comma-separated list of dimensions (e.g., "country,city").
        metrics: Comma-separated list of metrics (e.g., "activeUsers,sessions").
        date_ranges: JSON string with date ranges (e.g., '[{"startDate": "7daysAgo", "endDate": "today"}]').
        GOOGLE_SERVICE_ACCOUNT_JSON: Google service account JSON string.
        GOOGLE_ACCESS_TOKEN: Google OAuth access token (alternative to service account).
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

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    if not property_id:
        return validation_error("property_id is required")

    # Build URL and method based on operation
    base_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}"
    url: Optional[str] = None
    method = "POST"
    payload = None

    if operation == "run_report":
        url = f"{base_url}:runReport"
        payload = {}
        if dimensions:
            payload["dimensions"] = [{"name": d.strip()} for d in dimensions.split(",")]
        if metrics:
            payload["metrics"] = [{"name": m.strip()} for m in metrics.split(",")]
        if date_ranges:
            try:
                payload["dateRanges"] = json.loads(date_ranges)
            except json.JSONDecodeError:
                return validation_error("date_ranges must be valid JSON")
    elif operation == "run_realtime_report":
        url = f"{base_url}:runRealtimeReport"
        payload = {}
        if dimensions:
            payload["dimensions"] = [{"name": d.strip()} for d in dimensions.split(",")]
        if metrics:
            payload["metrics"] = [{"name": m.strip()} for m in metrics.split(",")]
    elif operation == "get_metadata":
        url = f"{base_url}/metadata"
        method = "GET"

    if url is None:
        return error_output(f"Internal error: unhandled operation '{operation}'")

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
    }

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Google Analytics request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", {}).get("message", "Google Analytics API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
