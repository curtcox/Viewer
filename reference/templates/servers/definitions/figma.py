# ruff: noqa: F821, F706
"""Interact with Figma to manage files and comments."""

from __future__ import annotations

from typing import Any, Dict, Optional

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

_OPERATIONS = {
    "list_files": OperationDefinition(),
    "get_file": OperationDefinition(
        required=(RequiredField("file_key"),),
    ),
    "list_comments": OperationDefinition(
        required=(RequiredField("file_key"),),
    ),
    "get_comment": OperationDefinition(
        required=(RequiredField("file_key"), RequiredField("comment_id")),
    ),
    "create_comment": OperationDefinition(
        required=(RequiredField("file_key"), RequiredField("message")),
        payload_builder=lambda message, client_meta, **_: {
            "message": message,
            **({"client_meta": client_meta} if client_meta else {}),
        },
    ),
    "delete_comment": OperationDefinition(
        required=(RequiredField("file_key"), RequiredField("comment_id")),
    ),
}

_ENDPOINT_BUILDERS = {
    "list_files": lambda **_: "me/files",
    "get_file": lambda file_key, **_: f"files/{file_key}",
    "list_comments": lambda file_key, **_: f"files/{file_key}/comments",
    "get_comment": lambda file_key, comment_id, **_: f"files/{file_key}/comments/{comment_id}",
    "create_comment": lambda file_key, **_: f"files/{file_key}/comments",
    "delete_comment": lambda file_key, comment_id, **_: f"files/{file_key}/comments/{comment_id}",
}

_METHODS = {
    "create_comment": "POST",
    "delete_comment": "DELETE",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Personal Access Token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def _figma_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("err") or data.get("message") or "Figma API error"
    return "Figma API error"


def main(
    *,
    operation: str = "list_files",
    file_key: str = "",
    comment_id: str = "",
    message: str = "",
    client_meta: Optional[Dict[str, Any]] = None,
    FIGMA_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List files and manage comments in Figma."""

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not FIGMA_ACCESS_TOKEN:
        return error_output(
            "Missing FIGMA_ACCESS_TOKEN",
            status_code=401,
            details="Provide a personal access token from Figma account settings",
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        file_key=file_key,
        comment_id=comment_id,
        message=message,
        client_meta=client_meta,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    params: Dict[str, Any] = {}
    payload: Optional[Dict[str, Any]] = result if isinstance(result, dict) else None

    # Return preview if in dry-run mode
    base_url = "https://api.figma.com/v1"
    endpoint = _ENDPOINT_BUILDERS[operation](file_key=file_key, comment_id=comment_id)
    url = f"{base_url}/{endpoint}"
    method = _METHODS.get(operation, "GET")

    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                url=url,
                method=method,
                payload=payload,
                params=params if params else None,
            )
        }

    # Build request
    api_client = client or _DEFAULT_CLIENT
    headers = {
        "X-Figma-Token": FIGMA_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    empty_response_statuses = (204,) if operation == "delete_comment" else None
    empty_response_output = (
        {"success": True, "message": "Comment deleted successfully"}
        if operation == "delete_comment"
        else None
    )

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params if method == "GET" and params else None,
        json=payload if method == "POST" else None,
        timeout=timeout,
        error_parser=_figma_error_message,
        request_error_message="Figma request failed",
        empty_response_statuses=empty_response_statuses,
        empty_response_output=empty_response_output,
    )
