# ruff: noqa: F821, F706
from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    error_output,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()


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
        "auth": "oauth",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _extract_error_message(data: Dict[str, Any]) -> str:
    errors = data.get("errors", [])
    if isinstance(errors, list) and errors:
        error = errors[0]
        if isinstance(error, dict):
            message = error.get("message", "")
            if message:
                return message
    message = data.get("message", "")
    if message:
        return message
    return "eBay API error"


def main(
    *,
    operation: str = "search_items",
    item_id: str = "",
    query: str = "",
    category_id: str = "",
    limit: int = 10,
    EBAY_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with eBay Browse API to search and get items."""

    normalized_operation = operation.lower()

    if normalized_operation not in {
        "search_items",
        "get_item",
        "get_item_by_legacy_id",
    }:
        return validation_error("Unsupported operation", field="operation")

    if not EBAY_ACCESS_TOKEN:
        return error_output(
            "Missing EBAY_ACCESS_TOKEN",
            status_code=401,
            details="Provide an eBay OAuth access token.",
        )

    if normalized_operation == "search_items" and not query and not category_id:
        return validation_error(
            "Missing required query or category_id", field="query"
        )
    if normalized_operation in {"get_item", "get_item_by_legacy_id"} and not item_id:
        return validation_error("Missing required item_id", field="item_id")

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {EBAY_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = "https://api.ebay.com/buy/browse/v1"
    url = f"{base_url}/item_summary/search"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "search_items":
        params = {"limit": limit}
        if query:
            params["q"] = query
        if category_id:
            params["category_ids"] = category_id
    elif normalized_operation == "get_item":
        url = f"{base_url}/item/{item_id}"
    elif normalized_operation == "get_item_by_legacy_id":
        url = f"{base_url}/item/get_item_by_legacy_id"
        params = {"legacy_item_id": item_id}

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    try:
        response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("eBay request failed", status_code=status, details=str(exc))

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
            _extract_error_message(data),
            status_code=response.status_code,
            response=data,
        )

    return {"output": data}
