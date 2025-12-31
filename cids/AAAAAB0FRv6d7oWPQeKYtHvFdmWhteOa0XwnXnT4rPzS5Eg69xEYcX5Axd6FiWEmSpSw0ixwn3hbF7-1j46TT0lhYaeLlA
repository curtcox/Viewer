# ruff: noqa: F821, F706
"""Interact with Google Drive API to manage files and folders."""

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


_SCOPES = ("https://www.googleapis.com/auth/drive",)
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = GoogleAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_files",
    "get_file",
    "upload_file",
    "delete_file",
    "share_file",
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
    operation: str = "list_files",
    file_id: Optional[str] = None,
    query: Optional[str] = None,
    page_size: int = 10,
    file_name: Optional[str] = None,
    file_content: Optional[str] = None,
    mime_type: str = "text/plain",
    parent_folder_id: Optional[str] = None,
    email: Optional[str] = None,
    role: str = "reader",
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None,
    GOOGLE_ACCESS_TOKEN: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[GoogleAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Google Drive API.

    Args:
        operation: Operation to perform (list_files, get_file, upload_file, delete_file, share_file).
        file_id: File ID (required for get_file, delete_file, share_file).
        query: Search query for list_files (e.g., "name contains 'report'").
        page_size: Maximum number of files to return (default: 10).
        file_name: Name for the file (required for upload_file).
        file_content: Content for the file (required for upload_file).
        mime_type: MIME type for the file (default: text/plain).
        parent_folder_id: Parent folder ID for upload_file.
        email: Email address to share with (required for share_file).
        role: Permission role for share_file (reader, writer, commenter).
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

    # Build URL and method based on operation
    base_url = "https://www.googleapis.com/drive/v3"
    method = "GET"
    payload = None

    if operation == "list_files":
        url = f"{base_url}/files?pageSize={page_size}"
        if query:
            url += f"&q={query}"
    elif operation == "get_file":
        if not file_id:
            return validation_error("file_id is required for get_file operation")
        url = f"{base_url}/files/{file_id}?alt=media"
    elif operation == "upload_file":
        if not file_name or not file_content:
            return validation_error(
                "file_name and file_content are required for upload_file operation"
            )
        url = f"{base_url}/files?uploadType=multipart"
        method = "POST"
        metadata = {"name": file_name, "mimeType": mime_type}
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]
        payload = {"metadata": metadata, "content": file_content}
    elif operation == "delete_file":
        if not file_id:
            return validation_error("file_id is required for delete_file operation")
        url = f"{base_url}/files/{file_id}"
        method = "DELETE"
    elif operation == "share_file":
        if not file_id or not email:
            return validation_error(
                "file_id and email are required for share_file operation"
            )
        url = f"{base_url}/files/{file_id}/permissions"
        method = "POST"
        payload = {"type": "user", "role": role, "emailAddress": email}

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
            "Google Drive request failed", status_code=status, details=str(exc)
        )

    if operation == "delete_file":
        # DELETE returns 204 No Content on success
        if response.status_code == 204:
            return {"output": {"message": "File deleted successfully"}}

    if not response.ok:
        parsed = _parse_json_response(response)
        if "error" in parsed.get("output", {}):
            return parsed
        return error_output(
            parsed.get("error", {}).get("message", "Google Drive API error"),
            status_code=response.status_code,
            response=parsed,
        )

    parsed = _parse_json_response(response)
    if "error" in parsed.get("output", {}):
        return parsed
    return {"output": parsed}
