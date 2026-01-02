# ruff: noqa: F821, F706
"""Interact with GitHub repositories to list or create issues."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error
from server_utils.external_api.limit_validator import GITHUB_MAX_PER_PAGE, get_limit_info, validate_limit


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    owner: str,
    repo: str,
    operation: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
    per_page: Optional[int] = None,
) -> Dict[str, Any]:
    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    if operation == "get_issue" and params and "issue_number" in params:
        url = f"{base_url}/{params['issue_number']}"
        params = None
    else:
        url = base_url

    method = "POST" if operation == "create_issue" else "GET"

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    # Include limit constraint information for list operations
    if per_page is not None and operation == "list_issues":
        preview["limit_constraint"] = get_limit_info(per_page, GITHUB_MAX_PER_PAGE, "per_page")

    return preview


def main(
    owner: str,
    repo: str,
    *,
    operation: str = "list_issues",
    title: str = "",
    body: str = "",
    issue_number: Optional[int] = None,
    state: str = "open",
    labels: Optional[str] = None,
    per_page: int = 30,
    GITHUB_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List or create issues in a GitHub repository."""

    if not owner:
        return validation_error("Missing required owner", field="owner")
    if not repo:
        return validation_error("Missing required repo", field="repo")

    normalized_operation = operation.lower()
    if normalized_operation not in {"list_issues", "create_issue", "get_issue"}:
        return validation_error("Unsupported operation", field="operation")

    if not GITHUB_TOKEN:
        return error_output(
            "Missing GITHUB_TOKEN",
            status_code=401,
            details="Provide a personal access token with repo scope",
        )

    # Validate pagination parameter (per_page)
    # GitHub API enforces a maximum of 100 items per page
    if error := validate_limit(per_page, GITHUB_MAX_PER_PAGE, "per_page"):
        return error

    api_client = client or _DEFAULT_CLIENT

    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_issues":
        params = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = labels
    elif normalized_operation == "create_issue":
        if not title:
            return validation_error("Missing required title", field="title")
        payload = {"title": title}
        if body:
            payload["body"] = body
    elif normalized_operation == "get_issue":
        if issue_number is None:
            return validation_error("Missing required issue_number", field="issue_number")
        params = {"issue_number": issue_number}

    if dry_run:
        preview = _build_preview(
            owner=owner,
            repo=repo,
            operation=normalized_operation,
            payload=payload,
            params=params,
            per_page=per_page if normalized_operation == "list_issues" else None,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    url = base_url
    if normalized_operation == "get_issue" and params:
        url = f"{base_url}/{params['issue_number']}"
        params = None

    try:
        if normalized_operation == "create_issue":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("GitHub request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        return error_output(
            data.get("message", "GitHub API error"),
            status_code=response.status_code,
            response=data,
        )

    return {"output": data}
