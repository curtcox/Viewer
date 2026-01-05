# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_projects",
    "get_project",
    "list_todolists",
    "list_todos",
    "get_todo",
    "create_todo",
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
        message = "Basecamp API error"
        if isinstance(data, dict):
            error_msg = data.get("error")
            if error_msg:
                message = error_msg if isinstance(error_msg, str) else str(error_msg)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_projects",
    account_id: str = "",
    project_id: str = "",
    todolist_id: str = "",
    todo_id: str = "",
    content: str = "",
    description: str = "",
    BASECAMP_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Basecamp projects and todos."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not BASECAMP_ACCESS_TOKEN:
        return error_output(
            "Missing BASECAMP_ACCESS_TOKEN",
            status_code=401,
            details="Provide an access token to authenticate Basecamp API calls.",
        )

    if not account_id:
        return error_output(
            "Missing account_id",
            status_code=400,
            details="Provide an account_id for Basecamp API calls.",
        )

    if normalized_operation == "get_project" and not project_id:
        return validation_error("Missing required project_id", field="project_id")

    if normalized_operation == "list_todolists" and not project_id:
        return validation_error("Missing required project_id", field="project_id")

    if normalized_operation == "list_todos" and not todolist_id:
        return validation_error("Missing required todolist_id", field="todolist_id")

    if normalized_operation == "get_todo" and not todo_id:
        return validation_error("Missing required todo_id", field="todo_id")

    if normalized_operation == "create_todo" and not todolist_id:
        return validation_error("Missing required todolist_id for create_todo", field="todolist_id")

    if normalized_operation == "create_todo" and not content:
        return validation_error("Missing required content", field="content")

    base_url = f"https://3.basecampapi.com/{account_id}"
    url = f"{base_url}/projects.json"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_projects":
        url = f"{base_url}/projects.json"
    elif normalized_operation == "get_project":
        url = f"{base_url}/projects/{project_id}.json"
    elif normalized_operation == "list_todolists":
        url = f"{base_url}/projects/{project_id}/todolists.json"
    elif normalized_operation == "list_todos":
        url = f"{base_url}/buckets/{project_id}/todolists/{todolist_id}/todos.json"
    elif normalized_operation == "get_todo":
        url = f"{base_url}/buckets/{project_id}/todos/{todo_id}.json"
    elif normalized_operation == "create_todo":
        url = f"{base_url}/buckets/{project_id}/todolists/{todolist_id}/todos.json"
        method = "POST"
        payload = {"content": content}
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
        "Authorization": f"Bearer {BASECAMP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Viewer App (contact@example.com)",
    }

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Basecamp request failed", status_code=status, details=str(exc))

    return _handle_response(response)
