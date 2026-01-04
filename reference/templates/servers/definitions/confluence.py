# ruff: noqa: F821, F706
from typing import Any, Dict, Optional
import base64

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_spaces",
    "get_space",
    "list_pages",
    "get_page",
    "create_page",
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
        message = "Confluence API error"
        if isinstance(data, dict):
            error_msg = data.get("message")
            if error_msg:
                message = error_msg
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_spaces",
    space_key: str = "",
    page_id: str = "",
    title: str = "",
    content: str = "",
    CONFLUENCE_API_TOKEN: str = "",
    CONFLUENCE_EMAIL: str = "",
    CONFLUENCE_DOMAIN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Confluence Cloud spaces and pages."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not CONFLUENCE_API_TOKEN:
        return error_output(
            "Missing CONFLUENCE_API_TOKEN",
            status_code=401,
            details="Provide an API token to authenticate Confluence API calls.",
        )

    if not CONFLUENCE_EMAIL:
        return error_output(
            "Missing CONFLUENCE_EMAIL",
            status_code=401,
            details="Provide an email to authenticate Confluence API calls.",
        )

    if not CONFLUENCE_DOMAIN:
        return error_output(
            "Missing CONFLUENCE_DOMAIN",
            status_code=401,
            details="Provide a domain (e.g., yourcompany.atlassian.net) for Confluence API calls.",
        )

    if normalized_operation == "get_space" and not space_key:
        return validation_error("Missing required space_key", field="space_key")

    if normalized_operation == "list_pages" and not space_key:
        return validation_error("Missing required space_key", field="space_key")

    if normalized_operation == "get_page" and not page_id:
        return validation_error("Missing required page_id", field="page_id")

    if normalized_operation == "create_page" and not space_key:
        return validation_error("Missing required space_key for create_page", field="space_key")

    if normalized_operation == "create_page" and not title:
        return validation_error("Missing required title", field="title")

    base_url = f"https://{CONFLUENCE_DOMAIN}/wiki/rest/api"
    url = f"{base_url}/space"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_spaces":
        url = f"{base_url}/space"
    elif normalized_operation == "get_space":
        url = f"{base_url}/space/{space_key}"
    elif normalized_operation == "list_pages":
        url = f"{base_url}/space/{space_key}/content/page"
    elif normalized_operation == "get_page":
        url = f"{base_url}/content/{page_id}"
    elif normalized_operation == "create_page":
        url = f"{base_url}/content"
        method = "POST"
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content or "<p>Page content</p>",
                    "representation": "storage",
                }
            },
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

    # Confluence uses Basic Auth with email:token
    auth_string = f"{CONFLUENCE_EMAIL}:{CONFLUENCE_API_TOKEN}"
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
        return error_output("Confluence request failed", status_code=status, details=str(exc))

    return _handle_response(response)
