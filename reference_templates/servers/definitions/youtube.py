# ruff: noqa: F821, F706
"""Interact with YouTube Data API to manage videos and channels."""

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


_SCOPES = ("https://www.googleapis.com/auth/youtube",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_videos",
    "get_video",
    "search_videos",
    "list_channels",
    "list_comments",
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
    operation: str = "search_videos",
    video_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    query: Optional[str] = None,
    max_results: int = 10,
    part: str = "snippet",
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    YOUTUBE_API_KEY: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with YouTube Data API.

    Args:
        operation: Operation to perform (list_videos, get_video, search_videos, list_channels, list_comments).
        video_id: Video ID (required for get_video, list_comments).
        channel_id: Channel ID (required for list_channels).
        query: Search query (required for search_videos).
        max_results: Maximum number of results to return (default: 10).
        part: Parts to include in response (default: snippet).
        GOOGLE_SERVICE_ACCOUNT_JSON: Google service account JSON string.
        GOOGLE_ACCESS_TOKEN: Google OAuth access token (alternative to service account).
        YOUTUBE_API_KEY: YouTube Data API key (alternative to OAuth).
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

    if not GOOGLE_SERVICE_ACCOUNT_JSON and not GOOGLE_ACCESS_TOKEN and not YOUTUBE_API_KEY:
        return error_output(
            "Missing credentials",
            status_code=401,
            details="Provide GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_ACCESS_TOKEN, or YOUTUBE_API_KEY.",
        )

    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Valid operations: {', '.join(_SUPPORTED_OPERATIONS)}"
        )

    # Build URL and method based on operation
    base_url = "https://www.googleapis.com/youtube/v3"
    method = "GET"
    payload = None

    if operation == "list_videos":
        if not video_id:
            return validation_error("video_id is required for list_videos operation")
        url = f"{base_url}/videos?id={video_id}&part={part}&maxResults={max_results}"
    elif operation == "get_video":
        if not video_id:
            return validation_error("video_id is required for get_video operation")
        url = f"{base_url}/videos?id={video_id}&part={part}"
    elif operation == "search_videos":
        if not query:
            return validation_error("query is required for search_videos operation")
        url = f"{base_url}/search?q={query}&part={part}&maxResults={max_results}&type=video"
    elif operation == "list_channels":
        if not channel_id:
            return validation_error("channel_id is required for list_channels operation")
        url = f"{base_url}/channels?id={channel_id}&part={part}"
    elif operation == "list_comments":
        if not video_id:
            return validation_error("video_id is required for list_comments operation")
        url = f"{base_url}/commentThreads?videoId={video_id}&part={part}&maxResults={max_results}"

    if dry_run:
        return {"output": _build_preview(operation=operation, url=url, method=method, payload=payload)}

    # Get access token or use API key
    headers = {"Content-Type": "application/json"}
    
    if YOUTUBE_API_KEY:
        url += f"&key={YOUTUBE_API_KEY}"
    elif GOOGLE_SERVICE_ACCOUNT_JSON:
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
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        headers["Authorization"] = f"Bearer {GOOGLE_ACCESS_TOKEN}"

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
            "YouTube API request failed", status_code=status, details=str(exc)
        )

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", {}).get("message", "YouTube API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
