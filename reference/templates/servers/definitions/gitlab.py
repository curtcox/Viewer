# ruff: noqa: F821, F706
"""Interact with GitLab projects to list or create issues and merge requests."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    project_id: str,
    operation: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
    gitlab_url: str,
) -> Dict[str, Any]:
    base_url = f"{gitlab_url}/api/v4/projects/{project_id}"
    
    if operation == "list_projects":
        url = f"{gitlab_url}/api/v4/projects"
        method = "GET"
    elif operation == "get_project":
        url = base_url
        method = "GET"
    elif operation == "list_issues":
        url = f"{base_url}/issues"
        method = "GET"
    elif operation == "get_issue":
        if params and "issue_iid" in params:
            url = f"{base_url}/issues/{params['issue_iid']}"
            params = {k: v for k, v in params.items() if k != "issue_iid"}
        else:
            url = f"{base_url}/issues"
        method = "GET"
    elif operation == "create_issue":
        url = f"{base_url}/issues"
        method = "POST"
    elif operation == "list_merge_requests":
        url = f"{base_url}/merge_requests"
        method = "GET"
    elif operation == "get_merge_request":
        if params and "mr_iid" in params:
            url = f"{base_url}/merge_requests/{params['mr_iid']}"
            params = {k: v for k, v in params.items() if k != "mr_iid"}
        else:
            url = f"{base_url}/merge_requests"
        method = "GET"
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

    normalized_operation = operation.lower()
    valid_operations = {
        "list_projects", "get_project", 
        "list_issues", "get_issue", "create_issue",
        "list_merge_requests", "get_merge_request"
    }
    
    if normalized_operation not in valid_operations:
        return validation_error(
            f"Unsupported operation: {operation}. Must be one of {', '.join(sorted(valid_operations))}",
            field="operation"
        )

    # Validate required parameters based on operation
    if normalized_operation not in {"list_projects"} and not project_id:
        return validation_error("Missing required project_id", field="project_id")

    if normalized_operation == "get_issue" and not issue_iid:
        return validation_error("Missing required issue_iid for get_issue", field="issue_iid")

    if normalized_operation == "create_issue" and not title:
        return validation_error("Missing required title for create_issue", field="title")

    if normalized_operation == "get_merge_request" and not mr_iid:
        return validation_error("Missing required mr_iid for get_merge_request", field="mr_iid")

    if not GITLAB_ACCESS_TOKEN:
        return error_output(
            "Missing GITLAB_ACCESS_TOKEN",
            status_code=401,
            details="Provide a personal access token or OAuth token with api scope",
        )

    # Build parameters and payload
    params: Dict[str, Any] = {"per_page": per_page, "page": page}
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation in {"list_issues", "list_merge_requests"}:
        if state:
            params["state"] = state
        if labels:
            params["labels"] = labels
    elif normalized_operation == "get_issue":
        params["issue_iid"] = issue_iid
    elif normalized_operation == "get_merge_request":
        params["mr_iid"] = mr_iid
    elif normalized_operation == "create_issue":
        payload = {"title": title}
        if description:
            payload["description"] = description
        if labels:
            payload["labels"] = labels

    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                project_id=project_id,
                operation=normalized_operation,
                payload=payload,
                params=params if normalized_operation != "create_issue" else None,
                gitlab_url=GITLAB_URL,
            )
        }

    # Build request
    use_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {GITLAB_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    base_url = f"{GITLAB_URL}/api/v4"
    
    if normalized_operation == "list_projects":
        url = f"{base_url}/projects"
        method = "GET"
    elif normalized_operation == "get_project":
        url = f"{base_url}/projects/{project_id}"
        method = "GET"
        params = {}
    elif normalized_operation == "list_issues":
        url = f"{base_url}/projects/{project_id}/issues"
        method = "GET"
    elif normalized_operation == "get_issue":
        url = f"{base_url}/projects/{project_id}/issues/{issue_iid}"
        method = "GET"
        params = {}
    elif normalized_operation == "create_issue":
        url = f"{base_url}/projects/{project_id}/issues"
        method = "POST"
        params = {}
    elif normalized_operation == "list_merge_requests":
        url = f"{base_url}/projects/{project_id}/merge_requests"
        method = "GET"
    elif normalized_operation == "get_merge_request":
        url = f"{base_url}/projects/{project_id}/merge_requests/{mr_iid}"
        method = "GET"
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
                f"GitLab API error: {response.status_code}",
                status_code=response.status_code,
                details=response.text[:500] if response.text else "No response body",
            )

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return error_output(
                "Invalid JSON response from GitLab API",
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
