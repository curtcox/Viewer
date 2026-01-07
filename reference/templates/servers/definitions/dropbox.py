# ruff: noqa: F821, F706
"""Interact with Dropbox to manage files and folders."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()

_ENDPOINT_MAP = {
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

_OPERATIONS = {
    "list_folder": OperationDefinition(
        payload_builder=lambda path, **_: {"path": path or "", "recursive": False}
    ),
    "get_metadata": OperationDefinition(
        required=(RequiredField("path"),),
        payload_builder=lambda path, **_: {"path": path},
    ),
    "download": OperationDefinition(
        required=(RequiredField("path"),),
        payload_builder=lambda path, **_: {"path": path},
    ),
    "upload": OperationDefinition(
        required=(RequiredField("path"), RequiredField("content")),
        payload_builder=lambda path, content, mode, autorename, mute, **_: {
            "path": path,
            "content": content,
            "mode": mode,
            "autorename": autorename,
            "mute": mute,
        },
    ),
    "delete": OperationDefinition(
        required=(RequiredField("path"),),
        payload_builder=lambda path, **_: {"path": path},
    ),
    "create_folder": OperationDefinition(
        required=(RequiredField("path"),),
        payload_builder=lambda path, autorename, **_: {"path": path, "autorename": autorename},
    ),
    "move": OperationDefinition(
        required=(
            RequiredField("path", "Missing required path (from_path)"),
            RequiredField("to_path", "Missing required to_path"),
        ),
        payload_builder=lambda path, to_path, autorename, **_: {
            "from_path": path,
            "to_path": to_path,
            "autorename": autorename,
        },
    ),
    "copy": OperationDefinition(
        required=(
            RequiredField("path", "Missing required path (from_path)"),
            RequiredField("to_path", "Missing required to_path"),
        ),
        payload_builder=lambda path, to_path, autorename, **_: {
            "from_path": path,
            "to_path": to_path,
            "autorename": autorename,
        },
    ),
    "search": OperationDefinition(
        required=(RequiredField("query"),),
        payload_builder=lambda query, path, **_: {
            "query": query,
            "options": {
                "path": path or "",
                "max_results": 100,
            },
        },
    ),
    "get_account": OperationDefinition(),
}


def _build_preview(
    *,
    operation: str,
    path: Optional[str],
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    endpoint = _ENDPOINT_MAP.get(operation, operation)
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
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        path=path,
        to_path=to_path,
        query=query,
        mode=mode,
        autorename=autorename,
        mute=mute,
        content=content,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    if dry_run:
        preview = _build_preview(
            operation=operation,
            path=path,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Build URL based on operation
    endpoint = _ENDPOINT_MAP.get(operation, operation)
    url = f"https://api.dropboxapi.com/2/{endpoint}"

    if operation == "download":
        headers["Content-Type"] = "text/plain"
        headers["Dropbox-API-Arg"] = f'{{"path": "{path}"}}'

    if operation == "download":
        url = f"https://content.dropboxapi.com/2/{endpoint}"
        try:
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return error_output(
                "Dropbox request failed",
                status_code=status,
                details=str(exc),
            )
        if response.ok:
            return {
                "output": {
                    "file": "Binary file data",
                    "content_type": "application/octet-stream",
                }
            }
        try:
            data = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response",
                status_code=getattr(response, "status_code", None),
                details=getattr(response, "text", None),
            )
        error_msg = _dropbox_error_message(response, data)
        return error_output(error_msg, status_code=response.status_code, response=data)

    return execute_json_request(
        api_client,
        "POST",
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_dropbox_error_message,
        request_error_message="Dropbox request failed",
        include_exception_in_message=False,
    )


def _dropbox_error_message(_response: requests.Response, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("error_summary", data.get("error", {}).get(".tag", "Dropbox API error"))
    return "Dropbox API error"
