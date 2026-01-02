# ruff: noqa: F821, F706
"""Interact with GitHub repositories to list or create issues."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    CredentialValidator,
    ExternalApiClient,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
)
from server_utils.external_api.limit_validator import GITHUB_MAX_PER_PAGE, get_limit_info, validate_limit


_DEFAULT_CLIENT = ExternalApiClient()
_OPERATIONS = {"list_issues", "create_issue", "get_issue"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "create_issue": ["title"],
    "get_issue": ["issue_number"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


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

    # Validate required parameters
    if not owner:
        from server_utils.external_api import validation_error
        return validation_error("Missing required owner", field="owner")
    if not repo:
        from server_utils.external_api import validation_error
        return validation_error("Missing required repo", field="repo")

    # Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate credentials
    if error := CredentialValidator.require_secret(GITHUB_TOKEN, "GITHUB_TOKEN"):
        return error

    # Validate pagination parameter
    if error := validate_limit(per_page, GITHUB_MAX_PER_PAGE, "per_page"):
        return error

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {"title": title, "issue_number": issue_number},
    ):
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
        payload = {"title": title}
        if body:
            payload["body"] = body
    elif normalized_operation == "get_issue":
        params = {"issue_number": issue_number}

    url = base_url
    if normalized_operation == "get_issue":
        url = f"{base_url}/{issue_number}"
        params = None

    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method="POST" if normalized_operation == "create_issue" else "GET",
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        # Include limit constraint information for list operations
        if normalized_operation == "list_issues":
            preview["limit_constraint"] = get_limit_info(per_page, GITHUB_MAX_PER_PAGE, "per_page")
        return PreviewBuilder.dry_run_response(preview)

    try:
        if normalized_operation == "create_issue":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Extract error message from GitHub API response
    def extract_github_error(data: Dict[str, Any]) -> str:
        return data.get("message", "GitHub API error")

    return ResponseHandler.handle_json_response(response, extract_github_error)
