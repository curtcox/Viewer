# ruff: noqa: F821, F706
"""Interact with OneDrive API via Microsoft Graph."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
    error_output,
    validation_error,
)


_GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()

_OPERATIONS = {
    "list_items",
    "get_item",
    "upload_file",
    "download_file",
    "delete_item",
    "create_folder",
}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)

_PARAMETER_REQUIREMENTS = {
    "upload_file": ["file_name", "file_content"],
    "create_folder": ["folder_name"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


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
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {
            "file_name": file_name,
            "file_content": file_content,
            "folder_name": folder_name,
        },
    ):
        return error

    # Additional validation for operations requiring item_id or path
    if normalized_operation in ("get_item", "download_file", "delete_item") and not (item_id or path):
        return validation_error(f"operation={normalized_operation} requires item_id or path")

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

    headers["Content-Type"] = "application/json"

    # Build request based on operation
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_items":
        url = f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children" if path else f"{_GRAPH_API_BASE}/me/drive/root/children"
        params = {"$top": top}
        method = "GET"
    elif normalized_operation == "get_item":
        url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}" if item_id else f"{_GRAPH_API_BASE}/me/drive/root:{path}"
        method = "GET"
    elif normalized_operation == "upload_file":
        url = f"{_GRAPH_API_BASE}/me/drive/root:{path}/{file_name}:/content" if path else f"{_GRAPH_API_BASE}/me/drive/root:/{file_name}:/content"
        method = "PUT"
        payload = {"content": file_content}
    elif normalized_operation == "download_file":
        url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}/content" if item_id else f"{_GRAPH_API_BASE}/me/drive/root:{path}:/content"
        method = "GET"
    elif normalized_operation == "delete_item":
        url = f"{_GRAPH_API_BASE}/me/drive/items/{item_id}" if item_id else f"{_GRAPH_API_BASE}/me/drive/root:{path}"
        method = "DELETE"
    elif normalized_operation == "create_folder":
        url = f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children" if path else f"{_GRAPH_API_BASE}/me/drive/root/children"
        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        method = "POST"
    else:
        url = f"{_GRAPH_API_BASE}/{normalized_operation}"
        method = "GET"

    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Microsoft OAuth",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    # Execute request
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
        return ResponseHandler.handle_request_exception(exc)

    # Handle 204 No Content for delete
    if response.status_code == 204:
        return {"output": {"success": True, "message": "Resource deleted"}, "content_type": "application/json"}

    # Extract error message from Microsoft Graph response
    def extract_error(data: Dict[str, Any]) -> str:
        if isinstance(data, dict) and "error" in data:
            error_info = data["error"]
            if isinstance(error_info, dict):
                return error_info.get("message", "Microsoft Graph API error")
        return "Microsoft Graph API error"

    return ResponseHandler.handle_json_response(response, extract_error)
