# ruff: noqa: F821, F706
"""Interact with Miro boards to manage items and widgets."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    board_id: Optional[str],
    item_id: Optional[str],
    widget_id: Optional[str],
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = "https://api.miro.com/v2"
    
    if operation == "list_boards":
        url = f"{base_url}/boards"
        method = "GET"
    elif operation == "get_board":
        url = f"{base_url}/boards/{board_id}"
        method = "GET"
    elif operation == "list_items":
        url = f"{base_url}/boards/{board_id}/items"
        method = "GET"
    elif operation == "get_item":
        url = f"{base_url}/boards/{board_id}/items/{item_id}"
        method = "GET"
    elif operation == "create_item":
        url = f"{base_url}/boards/{board_id}/items"
        method = "POST"
    elif operation == "list_widgets":
        url = f"{base_url}/boards/{board_id}/widgets"
        method = "GET"
    elif operation == "get_widget":
        url = f"{base_url}/boards/{board_id}/widgets/{widget_id}"
        method = "GET"
    elif operation == "create_widget":
        url = f"{base_url}/boards/{board_id}/widgets"
        method = "POST"
    else:
        url = base_url
        method = "GET"

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
    operation: str = "list_boards",
    board_id: str = "",
    item_id: str = "",
    widget_id: str = "",
    item_type: str = "card",
    widget_type: str = "shape",
    data: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    MIRO_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List boards, items, and widgets in Miro."""

    normalized_operation = operation.lower()
    valid_operations = {
        "list_boards", "get_board",
        "list_items", "get_item", "create_item",
        "list_widgets", "get_widget", "create_widget"
    }
    
    if normalized_operation not in valid_operations:
        return validation_error(
            f"Unsupported operation: {operation}. Must be one of {', '.join(sorted(valid_operations))}",
            field="operation"
        )

    # Validate required parameters based on operation
    if normalized_operation not in {"list_boards"} and not board_id:
        return validation_error("Missing required board_id", field="board_id")

    if normalized_operation == "get_board" and not board_id:
        return validation_error("Missing required board_id for get_board", field="board_id")

    if normalized_operation == "get_item" and not item_id:
        return validation_error("Missing required item_id for get_item", field="item_id")

    if normalized_operation == "create_item" and not data:
        return validation_error("Missing required data for create_item", field="data")

    if normalized_operation == "get_widget" and not widget_id:
        return validation_error("Missing required widget_id for get_widget", field="widget_id")

    if normalized_operation == "create_widget" and not data:
        return validation_error("Missing required data for create_widget", field="data")

    if not MIRO_ACCESS_TOKEN:
        return error_output(
            "Missing MIRO_ACCESS_TOKEN",
            status_code=401,
            details="Provide an OAuth access token with boards:read or boards:write scope",
        )

    # Build parameters and payload
    params: Dict[str, Any] = {"limit": limit}
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "create_item":
        payload = {"type": item_type, "data": data}
    elif normalized_operation == "create_widget":
        payload = {"type": widget_type, "data": data}

    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                board_id=board_id,
                item_id=item_id,
                widget_id=widget_id,
                payload=payload,
                params=params if normalized_operation in {"list_boards", "list_items", "list_widgets"} else None,
            )
        }

    # Build request
    use_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    base_url = "https://api.miro.com/v2"
    
    if normalized_operation == "list_boards":
        url = f"{base_url}/boards"
        method = "GET"
    elif normalized_operation == "get_board":
        url = f"{base_url}/boards/{board_id}"
        method = "GET"
        params = {}
    elif normalized_operation == "list_items":
        url = f"{base_url}/boards/{board_id}/items"
        method = "GET"
    elif normalized_operation == "get_item":
        url = f"{base_url}/boards/{board_id}/items/{item_id}"
        method = "GET"
        params = {}
    elif normalized_operation == "create_item":
        url = f"{base_url}/boards/{board_id}/items"
        method = "POST"
        params = {}
    elif normalized_operation == "list_widgets":
        url = f"{base_url}/boards/{board_id}/widgets"
        method = "GET"
    elif normalized_operation == "get_widget":
        url = f"{base_url}/boards/{board_id}/widgets/{widget_id}"
        method = "GET"
        params = {}
    elif normalized_operation == "create_widget":
        url = f"{base_url}/boards/{board_id}/widgets"
        method = "POST"
        params = {}
    else:
        return validation_error("Unexpected operation", field="operation")

    try:
        response = use_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params if method == "GET" and params else None,
            json=payload if method == "POST" else None,
            timeout=timeout,
        )

        if response.status_code >= 400:
            return error_output(
                f"Miro API error: {response.status_code}",
                status_code=response.status_code,
                details=response.text[:500] if response.text else "No response body",
            )

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return error_output(
                "Invalid JSON response from Miro API",
                status_code=response.status_code,
                details=response.text[:500] if response.text else "No response body",
            )

        return {"output": data}

    except requests.exceptions.Timeout:
        return error_output(
            f"Request timed out after {timeout} seconds",
            status_code=408,
            details="Consider increasing the timeout parameter",
        )
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        return error_output(
            f"Request failed: {str(e)}",
            status_code=status_code,
            details=str(e),
        )
