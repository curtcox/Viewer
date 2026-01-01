# ruff: noqa: F821, F706
"""Interact with Dropbox to manage files and folders."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    path: Optional[str],
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    endpoint_map = {
        "list_folder": "files/list_folder",
        "get_metadata": "files/get_metadata",
        "download": "files/download",
        "upload": "files/upload",
        "delete": "files/delete_v2",
        "create_folder": "files/create_folder_v2",
        "move": "files/move_v2",
        "copy": "files/copy_v2",
        "search": "files/search_v2",
        "get_account": "users/get_current_account",
    }
    
    endpoint = endpoint_map.get(operation, operation)
    url = f"https://api.dropboxapi.com/2/{endpoint}"

    method = "POST"  # Most Dropbox API v2 endpoints use POST

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Bearer token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def main(
    *,
    operation: str = "list_folder",
    path: str = "",
    to_path: str = "",
    query: str = "",
    mode: str = "add",
    autorename: bool = False,
    mute: bool = False,
    content: str = "",
    DROPBOX_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage Dropbox files and folders.
    
    Operations:
    - list_folder: List contents of a folder
    - get_metadata: Get metadata for a file or folder
    - download: Download a file
    - upload: Upload a file
    - delete: Delete a file or folder
    - create_folder: Create a new folder
    - move: Move a file or folder
    - copy: Copy a file or folder
    - search: Search for files and folders
    - get_account: Get current account information
    """

    normalized_operation = operation.lower()
    valid_operations = {
        "list_folder",
        "get_metadata",
        "download",
        "upload",
        "delete",
        "create_folder",
        "move",
        "copy",
        "search",
        "get_account",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    if not DROPBOX_ACCESS_TOKEN:
        return error_output(
            "Missing DROPBOX_ACCESS_TOKEN",
            status_code=401,
            details="Provide an OAuth access token for Dropbox API",
        )

    api_client = client or _DEFAULT_CLIENT

    headers = {
        "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    # Validate and build payload based on operation
    if normalized_operation == "list_folder":
        if not path:
            path = ""  # Empty string means root folder
        payload = {"path": path if path else "", "recursive": False}
    elif normalized_operation == "get_metadata":
        if not path:
            return validation_error("Missing required path", field="path")
        payload = {"path": path}
    elif normalized_operation == "download":
        if not path:
            return validation_error("Missing required path", field="path")
        payload = {"path": path}
        headers["Content-Type"] = "text/plain"
        headers["Dropbox-API-Arg"] = f'{{"path": "{path}"}}'
    elif normalized_operation == "upload":
        if not path:
            return validation_error("Missing required path", field="path")
        if not content:
            return validation_error("Missing required content", field="content")
        payload = {
            "path": path,
            "mode": mode,
            "autorename": autorename,
            "mute": mute,
        }
    elif normalized_operation == "delete":
        if not path:
            return validation_error("Missing required path", field="path")
        payload = {"path": path}
    elif normalized_operation == "create_folder":
        if not path:
            return validation_error("Missing required path", field="path")
        payload = {"path": path, "autorename": autorename}
    elif normalized_operation == "move":
        if not path:
            return validation_error("Missing required path (from_path)", field="path")
        if not to_path:
            return validation_error("Missing required to_path", field="to_path")
        payload = {"from_path": path, "to_path": to_path, "autorename": autorename}
    elif normalized_operation == "copy":
        if not path:
            return validation_error("Missing required path (from_path)", field="path")
        if not to_path:
            return validation_error("Missing required to_path", field="to_path")
        payload = {"from_path": path, "to_path": to_path, "autorename": autorename}
    elif normalized_operation == "search":
        if not query:
            return validation_error("Missing required query", field="query")
        payload = {
            "query": query,
            "options": {
                "path": path if path else "",
                "max_results": 100,
            }
        }
    elif normalized_operation == "get_account":
        payload = None  # No payload needed

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            path=path,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build URL based on operation
    endpoint_map = {
        "list_folder": "files/list_folder",
        "get_metadata": "files/get_metadata",
        "download": "files/download",
        "upload": "files/upload",
        "delete": "files/delete_v2",
        "create_folder": "files/create_folder_v2",
        "move": "files/move_v2",
        "copy": "files/copy_v2",
        "search": "files/search_v2",
        "get_account": "users/get_current_account",
    }
    
    endpoint = endpoint_map.get(normalized_operation, normalized_operation)
    url = f"https://api.dropboxapi.com/2/{endpoint}"

    try:
        if normalized_operation == "download":
            # Download uses content download endpoint
            url = f"https://content.dropboxapi.com/2/{endpoint}"
        
        response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Dropbox request failed", status_code=status, details=str(exc))

    # Handle binary download
    if normalized_operation == "download" and response.ok:
        return {"output": {"file": "Binary file data", "content_type": "application/octet-stream"}}

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        error_msg = data.get("error_summary", data.get("error", {}).get(".tag", "Dropbox API error"))
        return error_output(error_msg, status_code=response.status_code, response=data)

    return {"output": data}
