# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_boards",
    "get_board",
    "list_items",
    "get_item",
    "create_item",
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
        "auth": "bearer",
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


def _handle_response(response: requests.Response) -> Dict[str, Any]:
    data = _parse_json_response(response)
    if "output" in data:
        return data

    if not response.ok:
        message = "Monday.com API error"
        if isinstance(data, dict):
            error_data = data.get("error_message") or data.get("error")
            if error_data:
                message = error_data if isinstance(error_data, str) else str(error_data)
        return error_output(message, status_code=response.status_code, details=data)

    if isinstance(data, dict) and "data" in data:
        return {"output": data["data"]}

    return {"output": data}


def main(
    *,
    operation: str = "list_boards",
    board_id: str = "",
    item_id: str = "",
    item_name: str = "",
    column_values: str = "",
    query: str = "",
    MONDAY_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Monday.com boards and items via GraphQL API."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not MONDAY_API_KEY:
        return error_output(
            "Missing MONDAY_API_KEY",
            status_code=401,
            details="Provide an API key to authenticate Monday.com API calls.",
        )

    if normalized_operation == "get_board" and not board_id:
        return validation_error("Missing required board_id", field="board_id")

    if normalized_operation == "list_items" and not board_id:
        return validation_error("Missing required board_id", field="board_id")

    if normalized_operation == "get_item" and not item_id:
        return validation_error("Missing required item_id", field="item_id")

    if normalized_operation == "create_item" and not board_id:
        return validation_error("Missing required board_id for create_item", field="board_id")

    if normalized_operation == "create_item" and not item_name:
        return validation_error("Missing required item_name", field="item_name")

    base_url = "https://api.monday.com/v2"
    method = "POST"
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_boards":
        if query:
            payload = {"query": query}
        else:
            payload = {"query": "query { boards { id name } }"}
    elif normalized_operation == "get_board":
        payload = {"query": f'query {{ boards(ids: {board_id}) {{ id name description }} }}'}
    elif normalized_operation == "list_items":
        payload = {"query": f'query {{ boards(ids: {board_id}) {{ items {{ id name }} }} }}'}
    elif normalized_operation == "get_item":
        payload = {"query": f'query {{ items(ids: {item_id}) {{ id name column_values {{ title value }} }} }}'}
    elif normalized_operation == "create_item":
        col_vals = f', column_values: {column_values}' if column_values else ''
        payload = {"query": f'mutation {{ create_item(board_id: {board_id}, item_name: "{item_name}"{col_vals}) {{ id }} }}'}

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=base_url,
            method=method,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    }

    api_client = client or _DEFAULT_CLIENT

    try:
        response = api_client.post(base_url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Monday.com request failed", status_code=status, details=str(exc))

    return _handle_response(response)
