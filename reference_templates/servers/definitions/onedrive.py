# ruff: noqa: F821, F706
"""Interact with OneDrive API via Microsoft Graph."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    error_output,
    validation_error,
)


_GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()


_SUPPORTED_OPERATIONS = {
    "list_items",
    "get_item",
    "upload_file",
    "download_file",
    "delete_item",
    "create_folder",
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
        "auth": "microsoft_oauth",
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
    operation: str = "list_items",
    item_id: Optional[str] = None,
    path: Optional[str] = None,
    file_name: Optional[str] = None,
    file_content: Optional[str] = None,
    folder_name: Optional[str] = None,
    top: int = 10,
    MICROSOFT_ACCESS_TOKEN: Optional[str] = None,
    MICROSOFT_TENANT_ID: Optional[str] = None,
    MICROSOFT_CLIENT_ID: Optional[str] = None,
    MICROSOFT_CLIENT_SECRET: Optional[str] = None,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    auth_manager: Optional[MicrosoftAuthManager] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with OneDrive API.

    Args:
        operation: Operation to perform (list_items, get_item, upload_file, download_file, delete_item, create_folder).
        item_id: Item ID (required for get_item, download_file, delete_item).
        path: Path to folder/file (alternative to item_id, e.g., "/Documents").
        file_name: File name for upload_file.
        file_content: File content for upload_file.
        folder_name: Folder name for create_folder.
        top: Maximum number of items to return (default: 10).
        MICROSOFT_ACCESS_TOKEN: Microsoft OAuth access token.
        MICROSOFT_TENANT_ID: Microsoft tenant ID (for client credentials flow).
        MICROSOFT_CLIENT_ID: Microsoft client ID (for client credentials flow).
        MICROSOFT_CLIENT_SECRET: Microsoft client secret (for client credentials flow).
        dry_run: When true, return preview without making API call.
        timeout: Request timeout in seconds.
        client: Optional ExternalApiClient for testing.
        auth_manager: Optional MicrosoftAuthManager for testing.
        context: Request context (optional).

    Returns:
        Dict with 'output' containing the API response or error.
    """
    # Validate operation
    if operation not in _SUPPORTED_OPERATIONS:
        return validation_error(
            f"Invalid operation: {operation}. Supported: {', '.join(sorted(_SUPPORTED_OPERATIONS))}"
        )

    # Validate operation-specific requirements
    if operation in ("get_item", "download_file", "delete_item") and not (item_id or path):
        return validation_error(f"operation={operation} requires item_id or path")

    if operation == "upload_file":
        if not file_name:
            return validation_error("upload_file requires file_name")
        if not file_content:
            return validation_error("upload_file requires file_content")

    if operation == "create_folder" and not folder_name:
        return validation_error("create_folder requires folder_name")

    # Get authentication
    auth_manager_instance = auth_manager or _DEFAULT_AUTH_MANAGER
    client_instance = client or _DEFAULT_CLIENT

    # Determine auth method
    if MICROSOFT_ACCESS_TOKEN:
        headers = {"Authorization": f"Bearer {MICROSOFT_ACCESS_TOKEN}"}
    elif MICROSOFT_TENANT_ID and MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET:
        auth_result = auth_manager_instance.get_authorization(
            tenant_id=MICROSOFT_TENANT_ID,
            client_id=MICROSOFT_CLIENT_ID,
            client_secret=MICROSOFT_CLIENT_SECRET,
            scopes=["https://graph.microsoft.com/.default"],
        )
        if "output" in auth_result:
            return auth_result
        headers = auth_result["headers"]
    else:
        return error_output(
            "Authentication required",
            details="Provide MICROSOFT_ACCESS_TOKEN or all of MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET",
        )

    # Build request based on operation
    if operation == "list_items":
        if path:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root/children"
        params = {"$top": top}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=params)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "get_item":
        if item_id:
            url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "upload_file":
        if path:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}/{file_name}:/content"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root:/{file_name}:/content"
        params = {}
        method = "PUT"
        payload = {"content": file_content}
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "download_file":
        if item_id:
            url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}/content"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}:/content"
        params = {}
        method = "GET"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "delete_item":
        if item_id:
            url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}"
        params = {}
        method = "DELETE"
        payload = None
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=None)
            return {"output": preview, "content_type": "application/json"}

    elif operation == "create_folder":
        if path:
            url = f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children"
        else:
            url = f"{_GRAPH_API_BASE}/me/drive/root/children"
        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        params = {}
        method = "POST"
        if dry_run:
            preview = _build_preview(operation=operation, url=url, method=method, payload=payload)
            return {"output": preview, "content_type": "application/json"}

    # Execute request
    headers["Content-Type"] = "application/json"

    try:
        if method == "GET":
            response = client_instance.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            response = client_instance.post(url, headers=headers, json=payload, timeout=timeout)
        elif method == "PUT":
            # For file upload, use text content
            response = client_instance.put(url, headers=headers, data=file_content, timeout=timeout)
        elif method == "DELETE":
            response = client_instance.delete(url, headers=headers, timeout=timeout)
        else:
            return error_output(f"Unsupported HTTP method: {method}")
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            f"Request failed: {exc}",
            status_code=status,
            details=str(exc),
        )

    if not response.ok:
        error_details = _parse_json_response(response)
        return error_output(
            f"API request failed: {response.status_code}",
            status_code=response.status_code,
            details=error_details,
        )

    # DELETE returns 204 with no content
    if response.status_code == 204:
        return {"output": {"success": True, "message": "Resource deleted"}, "content_type": "application/json"}

    result = _parse_json_response(response)
    if "output" in result:
        return result

    return {"output": result, "content_type": "application/json"}
