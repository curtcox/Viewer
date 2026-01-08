# ruff: noqa: F821, F706
"""Interact with GitLab projects to list or create issues and merge requests."""

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
    "list_projects": OperationDefinition(),
    "get_project": OperationDefinition(required=(RequiredField("project_id"),)),
    "list_issues": OperationDefinition(required=(RequiredField("project_id"),)),
    "get_issue": OperationDefinition(
        required=(RequiredField("project_id"), RequiredField("issue_iid"))
    ),
    "create_issue": OperationDefinition(
        required=(RequiredField("project_id"), RequiredField("title")),
        payload_builder=lambda title, description, labels, **_: {
            "title": title,
            **({"description": description} if description else {}),
            **({"labels": labels} if labels else {}),
        },
    ),
    "list_merge_requests": OperationDefinition(required=(RequiredField("project_id"),)),
    "get_merge_request": OperationDefinition(
        required=(RequiredField("project_id"), RequiredField("mr_iid"))
    ),
}

_METHODS = {
    "create_issue": "POST",
}


def _build_url(
    base_url: str,
    *,
    operation: str,
    project_id: str,
    issue_iid: Optional[int],
    mr_iid: Optional[int],
) -> str:
    if operation == "list_projects":
        return f"{base_url}/projects"
    if operation == "get_project":
        return f"{base_url}/projects/{project_id}"
    if operation == "list_issues":
        return f"{base_url}/projects/{project_id}/issues"
    if operation == "get_issue":
        return f"{base_url}/projects/{project_id}/issues/{issue_iid}"
    if operation == "create_issue":
        return f"{base_url}/projects/{project_id}/issues"
    if operation == "list_merge_requests":
        return f"{base_url}/projects/{project_id}/merge_requests"
    if operation == "get_merge_request":
        return f"{base_url}/projects/{project_id}/merge_requests/{mr_iid}"
    raise ValueError("Unsupported operation")


def _build_params(
    operation: str,
    *,
    per_page: int,
    page: int,
    state: str,
    labels: Optional[str],
) -> Optional[Dict[str, Any]]:
    if operation == "list_projects":
        return {"per_page": per_page, "page": page}
    if operation in {"list_issues", "list_merge_requests"}:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if state:
            params["state"] = state
        if labels:
            params["labels"] = labels
        return params
    return None


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
        "auth": "Bearer token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def main(
    *,
    operation: str = "list_projects",
    project_id: str = "",
    title: str = "",
    description: str = "",
    issue_iid: Optional[int] = None,
    mr_iid: Optional[int] = None,
    state: str = "opened",
    labels: Optional[str] = None,
    per_page: int = 20,
    page: int = 1,
    GITLAB_ACCESS_TOKEN: str = "",
    GITLAB_URL: str = "https://gitlab.com",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List projects, issues, and merge requests in GitLab."""

    if not GITLAB_ACCESS_TOKEN:
        return error_output(
            "Missing GITLAB_ACCESS_TOKEN",
            status_code=401,
            details="Provide a personal access token or OAuth token with api scope",
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        project_id=project_id,
        title=title,
        description=description,
        issue_iid=issue_iid,
        mr_iid=mr_iid,
        labels=labels,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    base_url = f"{GITLAB_URL}/api/v4"
    url = _build_url(
        base_url,
        operation=operation,
        project_id=project_id,
        issue_iid=issue_iid,
        mr_iid=mr_iid,
    )
    method = _METHODS.get(operation, "GET")
    params = _build_params(
        operation,
        per_page=per_page,
        page=page,
        state=state,
        labels=labels,
    )
    payload = result

    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                url=url,
                method=method,
                payload=payload,
                params=params,
            )
        }

    use_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {GITLAB_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        use_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_key="message",
        request_error_message="GitLab request failed",
    )
