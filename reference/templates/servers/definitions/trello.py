# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_boards",
    "get_board",
    "list_lists",
    "list_cards",
    "get_card",
    "create_card",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "api_key_and_token",
    }

    if params:
        preview["params"] = params
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
        message = "Trello API error"
        if isinstance(data, dict):
            message = data.get("message", message)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_boards",
    board_id: str = "",
    list_id: str = "",
    card_id: str = "",
    name: str = "",
    description: str = "",
    TRELLO_API_KEY: str = "",
    TRELLO_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Trello boards, lists, and cards."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not TRELLO_API_KEY:
        return error_output(
            "Missing TRELLO_API_KEY",
            status_code=401,
            details="Provide an API key to authenticate Trello API calls.",
        )

    if not TRELLO_TOKEN:
        return error_output(
            "Missing TRELLO_TOKEN",
            status_code=401,
            details="Provide a token to authenticate Trello API calls.",
        )

    if normalized_operation in ("get_board", "list_lists") and not board_id:
        return validation_error("Missing required board_id", field="board_id")

    if normalized_operation == "list_cards" and not list_id:
        return validation_error("Missing required list_id", field="list_id")

    if normalized_operation == "get_card" and not card_id:
        return validation_error("Missing required card_id", field="card_id")

    if normalized_operation == "create_card" and not name:
        return validation_error("Missing required name", field="name")

    if normalized_operation == "create_card" and not list_id:
        return validation_error("Missing required list_id for create_card", field="list_id")

    base_url = "https://api.trello.com/1"
    auth_params = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
    url = f"{base_url}/boards"
    method = "GET"
    params: Optional[Dict[str, Any]] = auth_params.copy()
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_boards":
        url = f"{base_url}/members/me/boards"
    elif normalized_operation == "get_board":
        url = f"{base_url}/boards/{board_id}"
    elif normalized_operation == "list_lists":
        url = f"{base_url}/boards/{board_id}/lists"
    elif normalized_operation == "list_cards":
        url = f"{base_url}/lists/{list_id}/cards"
    elif normalized_operation == "get_card":
        url = f"{base_url}/cards/{card_id}"
    elif normalized_operation == "create_card":
        url = f"{base_url}/cards"
        method = "POST"
        params["idList"] = list_id
        params["name"] = name
        if description:
            params["desc"] = description

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, params=params, timeout=timeout)
        else:
            response = api_client.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Trello request failed", status_code=status, details=str(exc))

    return _handle_response(response)
