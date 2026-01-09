# ruff: noqa: F821, F706
"""Interact with Webflow CMS and sites."""

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
_BASE_URL = "https://api.webflow.com"

_OPERATIONS = {
    "list_sites": OperationDefinition(),
    "get_site": OperationDefinition(required=(RequiredField("site_id"),)),
    "publish_site": OperationDefinition(
        required=(RequiredField("site_id"),),
        payload_builder=lambda live, **_: {"domains": ["live"] if live else []},
    ),
    "list_collections": OperationDefinition(required=(RequiredField("site_id"),)),
    "get_collection": OperationDefinition(required=(RequiredField("collection_id"),)),
    "list_items": OperationDefinition(required=(RequiredField("collection_id"),)),
    "get_item": OperationDefinition(
        required=(RequiredField("collection_id"), RequiredField("item_id"))
    ),
    "create_item": OperationDefinition(
        required=(RequiredField("collection_id"), RequiredField("fields")),
        payload_builder=lambda fields, **_: {"fields": fields},
    ),
    "update_item": OperationDefinition(
        required=(
            RequiredField("collection_id"),
            RequiredField("item_id"),
            RequiredField("fields"),
        ),
        payload_builder=lambda fields, **_: {
            "fields": fields,
            "_archived": False,
            "_draft": False,
        },
    ),
    "delete_item": OperationDefinition(
        required=(RequiredField("collection_id"), RequiredField("item_id"))
    ),
}

_METHODS = {
    "publish_site": "POST",
    "create_item": "POST",
    "update_item": "PUT",
    "delete_item": "DELETE",
}

_ENDPOINT_BUILDERS = {
    "list_sites": lambda base_url, **_: f"{base_url}/sites",
    "get_site": lambda base_url, site_id, **_: f"{base_url}/sites/{site_id}",
    "publish_site": lambda base_url, site_id, **_: (
        f"{base_url}/sites/{site_id}/publish"
    ),
    "list_collections": lambda base_url, site_id, **_: (
        f"{base_url}/sites/{site_id}/collections"
    ),
    "get_collection": lambda base_url, collection_id, **_: (
        f"{base_url}/collections/{collection_id}"
    ),
    "list_items": lambda base_url, collection_id, **_: (
        f"{base_url}/collections/{collection_id}/items"
    ),
    "get_item": lambda base_url, collection_id, item_id, **_: (
        f"{base_url}/collections/{collection_id}/items/{item_id}"
    ),
    "create_item": lambda base_url, collection_id, **_: (
        f"{base_url}/collections/{collection_id}/items"
    ),
    "update_item": lambda base_url, collection_id, item_id, **_: (
        f"{base_url}/collections/{collection_id}/items/{item_id}"
    ),
    "delete_item": lambda base_url, collection_id, item_id, **_: (
        f"{base_url}/collections/{collection_id}/items/{item_id}"
    ),
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Bearer token",
    }
    if payload:
        preview["payload"] = payload
    return preview


def _webflow_error_message(response: object, data: object) -> str:
    status_code = getattr(response, "status_code", None)
    if status_code == 401:
        return (
            "Invalid or expired WEBFLOW_API_TOKEN. Check your API token in Webflow Account Settings"
        )
    if status_code == 403:
        return (
            "Insufficient permissions for this operation. Check your API token has the required scopes"
        )
    if status_code == 404:
        return "Resource not found"
    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "Webflow API error"
    return "Webflow API error"


def main(
    *,
    operation: str = "list_sites",
    site_id: str = "",
    collection_id: str = "",
    item_id: str = "",
    fields: Optional[Dict[str, Any]] = None,
    live: bool = False,
    WEBFLOW_API_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List sites, collections, and manage CMS items in Webflow.

    Operations:
    - list_sites: List all sites
    - get_site: Get site details (requires site_id)
    - publish_site: Publish a site (requires site_id, supports live parameter)
    - list_collections: List all collections for a site (requires site_id)
    - get_collection: Get collection details (requires collection_id)
    - list_items: List all items in a collection (requires collection_id)
    - get_item: Get item details (requires collection_id and item_id)
    - create_item: Create a new item (requires collection_id and fields)
    - update_item: Update an item (requires collection_id, item_id, and fields)
    - delete_item: Delete an item (requires collection_id and item_id)

    Args:
        operation: The operation to perform
        site_id: The site ID (for site and collection operations)
        collection_id: The collection ID (for item operations)
        item_id: The item ID (for get/update/delete item operations)
        fields: Dictionary of field values for create/update operations
        live: Whether to publish to live domain (default: False publishes to staging)
        WEBFLOW_API_TOKEN: Webflow API token from account settings
        dry_run: If True, return preview without making actual API call
        timeout: Request timeout in seconds
        client: Optional ExternalApiClient for testing
        context: Request context
    """

    if operation not in _OPERATIONS:
        return validation_error(
            f"Unsupported operation: {operation}. Must be one of {', '.join(sorted(_OPERATIONS))}",
            field="operation",
        )

    if not WEBFLOW_API_TOKEN:
        return error_output(
            "Missing WEBFLOW_API_TOKEN. Get your API token from Webflow Account Settings > Integrations",
            status_code=401,
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        site_id=site_id,
        collection_id=collection_id,
        item_id=item_id,
        fields=fields,
        live=live,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    url = _ENDPOINT_BUILDERS[operation](
        base_url=_BASE_URL,
        site_id=site_id,
        collection_id=collection_id,
        item_id=item_id,
    )
    method = _METHODS.get(operation, "GET")
    payload = result

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            payload=payload,
        )
        return {"output": {"dry_run": True, "preview": preview}}

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "accept-version": "1.0.0",
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
        error_parser=_webflow_error_message,
        request_error_message="Webflow API request failed",
        empty_response_statuses=(204,),
        empty_response_output={"success": True},
    )
