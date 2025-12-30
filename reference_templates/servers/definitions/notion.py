"""Interact with Notion to search, retrieve, or create pages."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()

_API_BASE = "https://api.notion.com/v1"

_DEF_VERSION = "2022-06-28"


def _build_preview(
    *,
    operation: str,
    payload: Optional[Dict[str, Any]],
    url: str,
    method: str,
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "token",
    }
    if payload:
        preview["payload"] = payload
    return preview


def _build_create_payload(
    database_id: str, title: str, properties: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    base_properties: Dict[str, Any] = {
        "Name": {
            "title": [
                {
                    "text": {"content": title},
                }
            ]
        }
    }
    if properties:
        base_properties.update(properties)

    return {
        "parent": {"database_id": database_id},
        "properties": base_properties,
    }


def main(
    *,
    operation: str = "search",
    query: str = "",
    page_id: str = "",
    database_id: str = "",
    title: str = "",
    properties: Optional[Dict[str, Any]] = None,
    NOTION_TOKEN: str = "",
    notion_version: str = _DEF_VERSION,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Search, retrieve, or create pages in Notion."""

    normalized_operation = operation.lower()
    if normalized_operation not in {"search", "retrieve_page", "create_page"}:
        return validation_error("Unsupported operation", field="operation")

    if not NOTION_TOKEN:
        return error_output(
            "Missing NOTION_TOKEN",
            status_code=401,
            details="Provide a Notion integration token",
        )

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }

    api_client = client or _DEFAULT_CLIENT
    url = f"{_API_BASE}/search"
    payload: Optional[Dict[str, Any]] = None
    method = "POST"

    if normalized_operation == "search":
        payload = {"query": query} if query else {}
    elif normalized_operation == "retrieve_page":
        if not page_id:
            return validation_error("Missing required page_id", field="page_id")
        url = f"{_API_BASE}/pages/{page_id}"
        method = "GET"
    elif normalized_operation == "create_page":
        if not database_id:
            return validation_error("Missing required database_id", field="database_id")
        if not title:
            return validation_error("Missing required title", field="title")
        payload = _build_create_payload(database_id, title, properties)

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            payload=payload,
            url=url,
            method=method,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    try:
        if method == "GET":
            response = api_client.get(url, headers=headers, timeout=timeout)
        else:
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Notion request failed", status_code=status, details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=getattr(response, "status_code", None),
            details=getattr(response, "text", None),
        )

    if not getattr(response, "ok", False):
        message = data.get("message") or data.get("error") or "Notion API error"
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
