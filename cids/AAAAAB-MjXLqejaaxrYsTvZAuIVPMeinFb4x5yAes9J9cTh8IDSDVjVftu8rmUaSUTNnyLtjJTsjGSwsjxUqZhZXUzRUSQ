# ruff: noqa: F821, F706
"""Interact with OneDrive API via Microsoft Graph."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    MicrosoftAuthManager,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validation_error,
    validate_and_build_payload,
)


_GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
_DEFAULT_CLIENT = ExternalApiClient()
_DEFAULT_AUTH_MANAGER = MicrosoftAuthManager()

_OPERATIONS = {
    "list_items": OperationDefinition(
        payload_builder=lambda path, top, **_: {
            "method": "GET",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children"
                if path
                else f"{_GRAPH_API_BASE}/me/drive/root/children"
            ),
            "params": {"$top": top},
            "payload": None,
            "data": None,
        },
    ),
    "get_item": OperationDefinition(
        payload_builder=lambda item_id, path, **_: {
            "method": "GET",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/items/{item_id}"
                if item_id
                else f"{_GRAPH_API_BASE}/me/drive/root:{path}"
            ),
            "params": None,
            "payload": None,
            "data": None,
        },
    ),
    "upload_file": OperationDefinition(
        required=(RequiredField("file_name"), RequiredField("file_content")),
        payload_builder=lambda path, file_name, file_content, **_: {
            "method": "PUT",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/root:{path}/{file_name}:/content"
                if path
                else f"{_GRAPH_API_BASE}/me/drive/root:/{file_name}:/content"
            ),
            "params": None,
            "payload": None,
            "data": file_content,
        },
    ),
    "download_file": OperationDefinition(
        payload_builder=lambda item_id, path, **_: {
            "method": "GET",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/items/{item_id}/content"
                if item_id
                else f"{_GRAPH_API_BASE}/me/drive/root:{path}:/content"
            ),
            "params": None,
            "payload": None,
            "data": None,
        },
    ),
    "delete_item": OperationDefinition(
        payload_builder=lambda item_id, path, **_: {
            "method": "DELETE",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/items/{item_id}"
                if item_id
                else f"{_GRAPH_API_BASE}/me/drive/root:{path}"
            ),
            "params": None,
            "payload": None,
            "data": None,
        },
    ),
    "create_folder": OperationDefinition(
        required=(RequiredField("folder_name"),),
        payload_builder=lambda path, folder_name, **_: {
            "method": "POST",
            "url": (
                f"{_GRAPH_API_BASE}/me/drive/root:{path}:/children"
                if path
                else f"{_GRAPH_API_BASE}/me/drive/root/children"
            ),
            "params": None,
            "payload": {
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
            "data": None,
        },
    ),
}


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
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        item_id=item_id,
        path=path,
        file_name=file_name,
        file_content=file_content,
        folder_name=folder_name,
        top=top,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    if result is None:
        return validation_error("Unsupported operation", field="operation")

    if operation in ("get_item", "download_file", "delete_item") and not (item_id or path):
        return validation_error(f"operation={operation} requires item_id or path")

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

    method = result["method"]
    url = result["url"]
    params = result["params"]
    payload = result["payload"]
    data = result["data"]

    if dry_run:
        preview = {
            "operation": operation,
            "url": url,
            "method": method,
            "auth_type": "Microsoft OAuth",
            "params": params,
            "payload": payload,
            "data": "[REDACTED]" if data else None,
        }
        return {"output": {"preview": preview}}

    def extract_error(response_data: Dict[str, Any]) -> str:
        if isinstance(response_data, dict) and "error" in response_data:
            error_info = response_data["error"]
            if isinstance(error_info, dict):
                return error_info.get("message", "Microsoft Graph API error")
        return "Microsoft Graph API error"

    return execute_json_request(
        client_instance,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        data=data,
        timeout=timeout,
        error_parser=lambda _response, data: extract_error(data),
        empty_response_statuses=(204,),
        empty_response_output={"success": True, "message": "Resource deleted"},
    )
