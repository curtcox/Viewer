# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_spaces",
    "get_space",
    "list_lists",
    "list_tasks",
    "get_task",
    "create_task",
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
        "auth": "bearer",
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
        message = "ClickUp API error"
        if isinstance(data, dict):
            error_msg = data.get("err") or data.get("error")
            if error_msg:
                message = error_msg if isinstance(error_msg, str) else str(error_msg)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_spaces",
    team_id: str = "",
    space_id: str = "",
    list_id: str = "",
    task_id: str = "",
    name: str = "",
    description: str = "",
    CLICKUP_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with ClickUp spaces, lists, and tasks."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not CLICKUP_API_KEY:
        return error_output(
            "Missing CLICKUP_API_KEY",
            status_code=401,
            details="Provide an API key to authenticate ClickUp API calls.",
        )

    if normalized_operation == "list_spaces" and not team_id:
        return validation_error("Missing required team_id", field="team_id")

    if normalized_operation == "get_space" and not space_id:
        return validation_error("Missing required space_id", field="space_id")

    if normalized_operation == "list_lists" and not space_id:
        return validation_error("Missing required space_id", field="space_id")

    if normalized_operation == "list_tasks" and not list_id:
        return validation_error("Missing required list_id", field="list_id")

    if normalized_operation == "get_task" and not task_id:
        return validation_error("Missing required task_id", field="task_id")

    if normalized_operation == "create_task" and not list_id:
        return validation_error("Missing required list_id for create_task", field="list_id")

    if normalized_operation == "create_task" and not name:
        return validation_error("Missing required name", field="name")

    base_url = "https://api.clickup.com/api/v2"
    url = f"{base_url}/spaces"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_spaces":
        url = f"{base_url}/team/{team_id}/space"
    elif normalized_operation == "get_space":
        url = f"{base_url}/space/{space_id}"
    elif normalized_operation == "list_lists":
        url = f"{base_url}/space/{space_id}/list"
    elif normalized_operation == "list_tasks":
        url = f"{base_url}/list/{list_id}/task"
    elif normalized_operation == "get_task":
        url = f"{base_url}/task/{task_id}"
    elif normalized_operation == "create_task":
        url = f"{base_url}/list/{list_id}/task"
        method = "POST"
        payload = {"name": name}
        if description:
            payload["description"] = description

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json",
    }

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("ClickUp request failed", status_code=status, details=str(exc))

    return _handle_response(response)
