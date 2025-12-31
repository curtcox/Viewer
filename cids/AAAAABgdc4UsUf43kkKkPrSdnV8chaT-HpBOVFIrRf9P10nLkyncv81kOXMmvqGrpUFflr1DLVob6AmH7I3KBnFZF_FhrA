# ruff: noqa: F821, F706
from typing import Any, Dict, Optional
import base64

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_projects",
    "get_project",
    "list_issues",
    "get_issue",
    "create_issue",
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
        "auth": "basic",
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
        message = "Jira API error"
        if isinstance(data, dict):
            error_messages = data.get("errorMessages", [])
            if error_messages and isinstance(error_messages, list):
                message = error_messages[0]
            elif "message" in data:
                message = data["message"]
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_projects",
    project_key: str = "",
    issue_key: str = "",
    jql: str = "",
    summary: str = "",
    description: str = "",
    issue_type: str = "Task",
    JIRA_API_TOKEN: str = "",
    JIRA_EMAIL: str = "",
    JIRA_DOMAIN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Jira Cloud projects and issues."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not JIRA_API_TOKEN:
        return error_output(
            "Missing JIRA_API_TOKEN",
            status_code=401,
            details="Provide an API token to authenticate Jira API calls.",
        )

    if not JIRA_EMAIL:
        return error_output(
            "Missing JIRA_EMAIL",
            status_code=401,
            details="Provide an email to authenticate Jira API calls.",
        )

    if not JIRA_DOMAIN:
        return error_output(
            "Missing JIRA_DOMAIN",
            status_code=401,
            details="Provide a domain (e.g., yourcompany.atlassian.net) for Jira API calls.",
        )

    if normalized_operation == "get_project" and not project_key:
        return validation_error("Missing required project_key", field="project_key")

    if normalized_operation == "list_issues" and not jql:
        return validation_error("Missing required jql", field="jql")

    if normalized_operation == "get_issue" and not issue_key:
        return validation_error("Missing required issue_key", field="issue_key")

    if normalized_operation == "create_issue" and not project_key:
        return validation_error("Missing required project_key for create_issue", field="project_key")

    if normalized_operation == "create_issue" and not summary:
        return validation_error("Missing required summary", field="summary")

    base_url = f"https://{JIRA_DOMAIN}/rest/api/3"
    url = f"{base_url}/project"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_projects":
        url = f"{base_url}/project"
    elif normalized_operation == "get_project":
        url = f"{base_url}/project/{project_key}"
    elif normalized_operation == "list_issues":
        url = f"{base_url}/search"
        params = {"jql": jql}
    elif normalized_operation == "get_issue":
        url = f"{base_url}/issue/{issue_key}"
    elif normalized_operation == "create_issue":
        url = f"{base_url}/issue"
        method = "POST"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
        }
        if description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Jira uses Basic Auth with email:token
    auth_string = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
    auth_header = f"Basic {auth_bytes.decode('utf-8')}"

    headers = {
        "Authorization": auth_header,
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
        return error_output("Jira request failed", status_code=status, details=str(exc))

    return _handle_response(response)
