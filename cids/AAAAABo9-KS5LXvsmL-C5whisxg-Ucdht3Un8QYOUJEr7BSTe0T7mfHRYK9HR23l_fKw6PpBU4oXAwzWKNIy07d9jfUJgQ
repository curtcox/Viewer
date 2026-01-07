# ruff: noqa: F821, F706
"""Interact with Box to manage files and folders."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    CredentialValidator,
    ExternalApiClient,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
)


_DEFAULT_CLIENT = ExternalApiClient()
_OPERATIONS = {
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
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "get_file": ["file_id"],
    "download_file": ["file_id"],
    "upload_file": ["name", "content"],
    "delete_file": ["file_id"],
    "delete_folder": ["folder_id"],
    "create_folder": ["name"],
    "copy_file": ["file_id", "parent_id"],
    "move_file": ["file_id", "parent_id"],
    "search": ["query"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


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

    # Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate credentials
    if error := CredentialValidator.require_secret(BOX_ACCESS_TOKEN, "BOX_ACCESS_TOKEN"):
        return error

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {
            "file_id": file_id,
            "folder_id": folder_id,
            "name": name,
            "content": content,
            "parent_id": parent_id,
            "query": query,
        },
    ):
        return error

    api_client = client or _DEFAULT_CLIENT

    base_url = "https://api.box.com/2.0"
    headers = {
        "Authorization": f"Bearer {BOX_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Set defaults
    if not folder_id:
        folder_id = "0"
    if not parent_id:
        parent_id = "0"

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    # Build request details based on operation
    if normalized_operation == "list_items":
        url = f"{base_url}/folders/{folder_id}/items"
        method = "GET"
    elif normalized_operation == "get_file":
        url = f"{base_url}/files/{file_id}"
        method = "GET"
    elif normalized_operation == "get_folder":
        url = f"{base_url}/folders/{folder_id}"
        method = "GET"
    elif normalized_operation == "download_file":
        url = f"{base_url}/files/{file_id}/content"
        method = "GET"
    elif normalized_operation == "upload_file":
        url = "https://upload.box.com/api/2.0/files/content"
        method = "POST"
        payload = {"name": name, "parent": {"id": parent_id}}
    elif normalized_operation == "delete_file":
        url = f"{base_url}/files/{file_id}"
        method = "DELETE"
    elif normalized_operation == "delete_folder":
        url = f"{base_url}/folders/{folder_id}"
        method = "DELETE"
        params = {"recursive": "true"}
    elif normalized_operation == "create_folder":
        url = f"{base_url}/folders"
        method = "POST"
        payload = {"name": name, "parent": {"id": parent_id}}
    elif normalized_operation == "copy_file":
        url = f"{base_url}/files/{file_id}/copy"
        method = "POST"
        payload = {"parent": {"id": parent_id}}
        if name:
            payload["name"] = name
    elif normalized_operation == "move_file":
        url = f"{base_url}/files/{file_id}"
        method = "PUT"
        payload = {"parent": {"id": parent_id}}
        if name:
            payload["name"] = name
    elif normalized_operation == "search":
        url = f"{base_url}/search"
        method = "GET"
        params = {"query": query, "limit": 100}
    elif normalized_operation == "get_user":
        url = f"{base_url}/users/me"
        method = "GET"
    else:
        url = f"{base_url}/{normalized_operation}"
        method = "GET"

    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    # Execute request
    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif method == "PUT":
            response = api_client.put(url, headers=headers, json=payload, timeout=timeout)
        elif method == "DELETE":
            response = api_client.delete(url, headers=headers, params=params, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Handle binary download
    if normalized_operation == "download_file" and response.ok:
        return {"output": {"file": "Binary file data", "content_type": "application/octet-stream"}}

    # Handle successful delete (204 No Content)
    if normalized_operation in {"delete_file", "delete_folder"} and response.status_code == 204:
        return {"output": {"message": "Successfully deleted"}}

    # Extract error message from Box API response
    def extract_error(data: Dict[str, Any]) -> str:
        if isinstance(data, dict):
            return data.get("message", data.get("error_description", "Box API error"))
        return "Box API error"

    return ResponseHandler.handle_json_response(response, extract_error)
