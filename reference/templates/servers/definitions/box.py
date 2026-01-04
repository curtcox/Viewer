# ruff: noqa: F821, F706
"""Interact with Box to manage files and folders."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    file_id: Optional[str],
    folder_id: Optional[str],
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = "https://api.box.com/2.0"
    
    if operation == "list_items" and folder_id:
        url = f"{base_url}/folders/{folder_id}/items"
    elif operation == "get_file" and file_id:
        url = f"{base_url}/files/{file_id}"
    elif operation == "get_folder" and folder_id:
        url = f"{base_url}/folders/{folder_id}"
    elif operation == "download_file" and file_id:
        url = f"{base_url}/files/{file_id}/content"
    elif operation == "upload_file":
        url = "https://upload.box.com/api/2.0/files/content"
    elif operation == "delete_file" and file_id:
        url = f"{base_url}/files/{file_id}"
    elif operation == "delete_folder" and folder_id:
        url = f"{base_url}/folders/{folder_id}"
    elif operation == "create_folder":
        url = f"{base_url}/folders"
    elif operation == "copy_file" and file_id:
        url = f"{base_url}/files/{file_id}/copy"
    elif operation == "move_file" and file_id:
        url = f"{base_url}/files/{file_id}"
    elif operation == "search":
        url = f"{base_url}/search"
    elif operation == "get_user":
        url = f"{base_url}/users/me"
    else:
        url = f"{base_url}/{operation}"

    method_map = {
        "upload_file": "POST",
        "create_folder": "POST",
        "copy_file": "POST",
        "move_file": "PUT",
        "delete_file": "DELETE",
        "delete_folder": "DELETE",
    }
    method = method_map.get(operation, "GET")

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
    operation: str = "list_items",
    file_id: str = "",
    folder_id: str = "0",
    parent_id: str = "0",
    name: str = "",
    query: str = "",
    content: str = "",
    BOX_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage Box files and folders.
    
    Operations:
    - list_items: List items in a folder (default: root folder with ID '0')
    - get_file: Get file metadata
    - get_folder: Get folder metadata
    - download_file: Download a file
    - upload_file: Upload a file
    - delete_file: Delete a file
    - delete_folder: Delete a folder
    - create_folder: Create a new folder
    - copy_file: Copy a file to a new location
    - move_file: Move a file to a new location
    - search: Search for files and folders
    - get_user: Get current user information
    """

    normalized_operation = operation.lower()
    valid_operations = {
        "list_items",
        "get_file",
        "get_folder",
        "download_file",
        "upload_file",
        "delete_file",
        "delete_folder",
        "create_folder",
        "copy_file",
        "move_file",
        "search",
        "get_user",
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    if not BOX_ACCESS_TOKEN:
        return error_output(
            "Missing BOX_ACCESS_TOKEN",
            status_code=401,
            details="Provide an OAuth access token for Box API",
        )

    api_client = client or _DEFAULT_CLIENT

    base_url = "https://api.box.com/2.0"
    headers = {
        "Authorization": f"Bearer {BOX_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    # Validate and build payload/params based on operation
    if normalized_operation == "list_items":
        # Default to root folder if not specified
        if not folder_id:
            folder_id = "0"
    elif normalized_operation == "get_file":
        if not file_id:
            return validation_error("Missing required file_id", field="file_id")
    elif normalized_operation == "get_folder":
        if not folder_id:
            folder_id = "0"
    elif normalized_operation == "download_file":
        if not file_id:
            return validation_error("Missing required file_id", field="file_id")
    elif normalized_operation == "upload_file":
        if not name:
            return validation_error("Missing required name", field="name")
        if not content:
            return validation_error("Missing required content", field="content")
        if not parent_id:
            parent_id = "0"
        payload = {
            "name": name,
            "parent": {"id": parent_id},
        }
    elif normalized_operation == "delete_file":
        if not file_id:
            return validation_error("Missing required file_id", field="file_id")
    elif normalized_operation == "delete_folder":
        if not folder_id:
            return validation_error("Missing required folder_id", field="folder_id")
        params = {"recursive": "true"}
    elif normalized_operation == "create_folder":
        if not name:
            return validation_error("Missing required name", field="name")
        if not parent_id:
            parent_id = "0"
        payload = {
            "name": name,
            "parent": {"id": parent_id},
        }
    elif normalized_operation == "copy_file":
        if not file_id:
            return validation_error("Missing required file_id", field="file_id")
        if not parent_id:
            return validation_error("Missing required parent_id (destination folder)", field="parent_id")
        payload = {
            "parent": {"id": parent_id},
        }
        if name:
            payload["name"] = name
    elif normalized_operation == "move_file":
        if not file_id:
            return validation_error("Missing required file_id", field="file_id")
        if not parent_id:
            return validation_error("Missing required parent_id (destination folder)", field="parent_id")
        payload = {
            "parent": {"id": parent_id},
        }
        if name:
            payload["name"] = name
    elif normalized_operation == "search":
        if not query:
            return validation_error("Missing required query", field="query")
        params = {"query": query, "limit": 100}

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            file_id=file_id,
            folder_id=folder_id,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build URL and make request
    if normalized_operation == "list_items":
        url = f"{base_url}/folders/{folder_id}/items"
    elif normalized_operation == "get_file":
        url = f"{base_url}/files/{file_id}"
    elif normalized_operation == "get_folder":
        url = f"{base_url}/folders/{folder_id}"
    elif normalized_operation == "download_file":
        url = f"{base_url}/files/{file_id}/content"
    elif normalized_operation == "upload_file":
        url = "https://upload.box.com/api/2.0/files/content"
    elif normalized_operation == "delete_file":
        url = f"{base_url}/files/{file_id}"
    elif normalized_operation == "delete_folder":
        url = f"{base_url}/folders/{folder_id}"
    elif normalized_operation == "create_folder":
        url = f"{base_url}/folders"
    elif normalized_operation == "copy_file":
        url = f"{base_url}/files/{file_id}/copy"
    elif normalized_operation == "move_file":
        url = f"{base_url}/files/{file_id}"
    elif normalized_operation == "search":
        url = f"{base_url}/search"
    elif normalized_operation == "get_user":
        url = f"{base_url}/users/me"
    else:
        url = f"{base_url}/{normalized_operation}"

    try:
        if normalized_operation == "upload_file":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif normalized_operation in {"create_folder", "copy_file"}:
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif normalized_operation == "move_file":
            response = api_client.put(url, headers=headers, json=payload, timeout=timeout)
        elif normalized_operation in {"delete_file", "delete_folder"}:
            response = api_client.delete(url, headers=headers, params=params, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Box request failed", status_code=status, details=str(exc))

    # Handle binary download
    if normalized_operation == "download_file" and response.ok:
        return {"output": {"file": "Binary file data", "content_type": "application/octet-stream"}}

    # Handle successful delete (204 No Content)
    if normalized_operation in {"delete_file", "delete_folder"} and response.status_code == 204:
        return {"output": {"message": "Successfully deleted"}}

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        error_msg = "Box API error"
        if isinstance(data, dict):
            error_msg = data.get("message", data.get("error_description", error_msg))
        return error_output(error_msg, status_code=response.status_code, response=data)

    return {"output": data}
