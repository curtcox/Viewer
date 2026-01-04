# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_projects",
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
        message = "Asana API error"
        if isinstance(data, dict):
            errors = data.get("errors")
            if isinstance(errors, list) and errors:
                message = errors[0].get("message", message)
            elif isinstance(data.get("error"), dict):
                message = data["error"].get("message", message)
            elif isinstance(data.get("error"), str):
                message = data["error"]
        return error_output(message, status_code=response.status_code, details=data)

    if isinstance(data, dict) and "data" in data:
        return {"output": data["data"]}

    return {"output": data}


def main(
    *,
    operation: str = "list_projects",
    workspace_gid: str = "",
    project_gid: str = "",
    task_gid: str = "",
    name: str = "",
    notes: str = "",
    assignee: str = "",
    limit: int = 20,
    ASANA_PAT: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Asana projects and tasks."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not ASANA_PAT:
        return error_output(
            "Missing ASANA_PAT",
            status_code=401,
            details="Provide a personal access token to authenticate Asana API calls.",
        )

    if normalized_operation == "list_projects" and not workspace_gid:
        return validation_error("Missing required workspace_gid", field="workspace_gid")

    if normalized_operation == "list_tasks" and not project_gid:
        return validation_error("Missing required project_gid", field="project_gid")

    if normalized_operation == "get_task" and not task_gid:
        return validation_error("Missing required task_gid", field="task_gid")

    if normalized_operation == "create_task" and not name:
        return validation_error("Missing required name", field="name")

    base_url = "https://app.asana.com/api/1.0"
    url = f"{base_url}/projects"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_projects":
        params = {"workspace": workspace_gid, "limit": limit}
    elif normalized_operation == "list_tasks":
        url = f"{base_url}/projects/{project_gid}/tasks"
        params = {"limit": limit}
    elif normalized_operation == "get_task":
        url = f"{base_url}/tasks/{task_gid}"
    elif normalized_operation == "create_task":
        url = f"{base_url}/tasks"
        method = "POST"
        payload = {"name": name}
        if workspace_gid:
            payload["workspace"] = workspace_gid
        if notes:
            payload["notes"] = notes
        if assignee:
            payload["assignee"] = assignee
        if project_gid:
            payload["projects"] = [project_gid]

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
        "Authorization": f"Bearer {ASANA_PAT}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    api_client = client or _DEFAULT_CLIENT

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Asana request failed", status_code=status, details=str(exc))

    return _handle_response(response)
