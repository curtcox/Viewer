# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_projects",
    "get_project",
    "list_tasks",
    "get_task",
    "create_task",
    "close_task",
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
        message = "Todoist API error"
        if isinstance(data, dict):
            error_msg = data.get("error") or data.get("message")
            if error_msg:
                message = error_msg if isinstance(error_msg, str) else str(error_msg)
        return error_output(message, status_code=response.status_code, details=data)

    # For successful responses with no content (like close_task)
    if response.status_code == 204:
        return {"output": {"success": True, "message": "Operation completed"}}

    return {"output": data}


def main(
    *,
    operation: str = "list_projects",
    project_id: str = "",
    task_id: str = "",
    content: str = "",
    description: str = "",
    priority: int = 1,
    TODOIST_API_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Todoist projects and tasks."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not TODOIST_API_TOKEN:
        return error_output(
            "Missing TODOIST_API_TOKEN",
            status_code=401,
            details="Provide an API token to authenticate Todoist API calls.",
        )

    if normalized_operation == "get_project" and not project_id:
        return validation_error("Missing required project_id", field="project_id")

    if normalized_operation == "list_tasks" and not project_id:
        return validation_error("Missing required project_id", field="project_id")

    if normalized_operation == "get_task" and not task_id:
        return validation_error("Missing required task_id", field="task_id")

    if normalized_operation == "close_task" and not task_id:
        return validation_error("Missing required task_id", field="task_id")

    if normalized_operation == "create_task" and not content:
        return validation_error("Missing required content", field="content")

    base_url = "https://api.todoist.com/rest/v2"
    url = f"{base_url}/projects"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_projects":
        url = f"{base_url}/projects"
    elif normalized_operation == "get_project":
        url = f"{base_url}/projects/{project_id}"
    elif normalized_operation == "list_tasks":
        url = f"{base_url}/tasks"
        params = {"project_id": project_id}
    elif normalized_operation == "get_task":
        url = f"{base_url}/tasks/{task_id}"
    elif normalized_operation == "create_task":
        url = f"{base_url}/tasks"
        method = "POST"
        payload = {"content": content, "priority": priority}
        if project_id:
            payload["project_id"] = project_id
        if description:
            payload["description"] = description
    elif normalized_operation == "close_task":
        url = f"{base_url}/tasks/{task_id}/close"
        method = "POST"

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
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
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
        return error_output("Todoist request failed", status_code=status, details=str(exc))

    return _handle_response(response)
