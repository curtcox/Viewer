# ruff: noqa: F821, F706
"""Interact with Wix to manage sites, collections, and items."""

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
    error_output,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "get_site",
    "list_collections",
    "get_collection",
    "query_items",
    "get_item",
    "create_item",
    "update_item",
    "delete_item",
}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)

_PARAMETER_REQUIREMENTS = {
    "get_collection": ["collection_id"],
    "query_items": ["data_collection_id"],
    "get_item": ["data_collection_id", "item_id"],
    "create_item": ["data_collection_id", "fields"],
    "update_item": ["data_collection_id", "item_id", "fields"],
    "delete_item": ["data_collection_id", "item_id"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


def main(
    *,
    operation: str = "list_collections",
    site_id: str = "",
    collection_id: str = "",
    item_id: str = "",
    data_collection_id: str = "",
    fields: Optional[Dict[str, Any]] = None,
    filter_json: Optional[Dict[str, Any]] = None,
    sort_json: Optional[Dict[str, Any]] = None,
    paging_limit: int = 50,
    paging_offset: int = 0,
    WIX_API_KEY: str = "",
    WIX_SITE_ID: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage sites, collections, and data items in Wix.

    Operations:
    - get_site: Get site details (requires site_id or WIX_SITE_ID)
    - list_collections: List all collections
    - get_collection: Get collection details (requires collection_id)
    - query_items: Query items from a collection (requires data_collection_id)
    - get_item: Get item details (requires data_collection_id and item_id)
    - create_item: Create a new item (requires data_collection_id and fields)
    - update_item: Update an item (requires data_collection_id, item_id, and fields)
    - delete_item: Delete an item (requires data_collection_id and item_id)

    Args:
        operation: The operation to perform
        site_id: The Wix site ID (falls back to WIX_SITE_ID)
        collection_id: The collection ID for get_collection
        item_id: The item ID for get/update/delete item operations
        data_collection_id: The collection ID for data operations
        fields: Dictionary of field values for create/update operations
        filter_json: Filter object for query_items (Wix query DSL)
        sort_json: Sort object for query_items
        paging_limit: Number of items to return (max 1000)
        paging_offset: Offset for pagination
        WIX_API_KEY: Wix API Key from Wix dashboard
        WIX_SITE_ID: Wix Site ID from Wix dashboard
        dry_run: If True, return preview without making actual API call
        timeout: Request timeout in seconds
        client: Optional ExternalApiClient for testing
        context: Request context
    """

    # Use WIX_SITE_ID if site_id not provided
    effective_site_id = site_id or WIX_SITE_ID

    # Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {
            "collection_id": collection_id,
            "data_collection_id": data_collection_id,
            "item_id": item_id,
            "fields": fields,
        },
    ):
        return error

    # Additional validation for get_site
    if normalized_operation == "get_site" and not effective_site_id:
        return validation_error("Missing required site_id or WIX_SITE_ID", field="site_id")

    # Validate API key
    if error := CredentialValidator.require_secret(WIX_API_KEY, "WIX_API_KEY"):
        return error

    # Build payload and params for operations
    payload = None
    params = None
    base_url = "https://www.wixapis.com"

    if normalized_operation == "query_items":
        payload = {
            "dataCollectionId": data_collection_id,
            "query": {
                "paging": {
                    "limit": paging_limit,
                    "offset": paging_offset,
                }
            }
        }
        if filter_json:
            payload["query"]["filter"] = filter_json
        if sort_json:
            payload["query"]["sort"] = sort_json
    elif normalized_operation == "create_item":
        payload = {
            "dataCollectionId": data_collection_id,
            "dataItem": {
                "data": fields
            }
        }
    elif normalized_operation == "update_item":
        payload = {
            "dataCollectionId": data_collection_id,
            "dataItem": {
                "id": item_id,
                "data": fields
            }
        }
    elif normalized_operation in {"get_item", "delete_item"}:
        params = {
            "dataCollectionId": data_collection_id
        }

    # Build URL and method based on operation
    if normalized_operation == "get_site":
        url = f"{base_url}/v2/sites/{effective_site_id}"
        method = "GET"
    elif normalized_operation == "list_collections":
        url = f"{base_url}/wix-data/v2/collections"
        method = "GET"
    elif normalized_operation == "get_collection":
        url = f"{base_url}/wix-data/v2/collections/{collection_id}"
        method = "GET"
    elif normalized_operation == "query_items":
        url = f"{base_url}/wix-data/v2/items/query"
        method = "POST"
    elif normalized_operation == "get_item":
        url = f"{base_url}/wix-data/v2/items/{item_id}"
        method = "GET"
    elif normalized_operation == "create_item":
        url = f"{base_url}/wix-data/v2/items"
        method = "POST"
    elif normalized_operation == "update_item":
        url = f"{base_url}/wix-data/v2/items/{item_id}"
        method = "PATCH"
    elif normalized_operation == "delete_item":
        url = f"{base_url}/wix-data/v2/items/{item_id}"
        method = "DELETE"
    else:
        url = base_url
        method = "GET"

    # Dry-run preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="API Key",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    # Make the actual API call
    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": WIX_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if payload else None,
            params=params if params else None,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Handle specific status codes
    if response.status_code == 401:
        return error_output(
            "Invalid or expired WIX_API_KEY. Check your API key in the Wix dashboard",
            status_code=401
        )
    elif response.status_code == 403:
        return error_output(
            "Insufficient permissions for this operation. Check your API key has the required permissions",
            status_code=403
        )
    elif response.status_code == 404:
        return error_output(
            f"Resource not found (collection_id={collection_id}, item_id={item_id})",
            status_code=404
        )

    # Handle 204 No Content
    if response.status_code == 204 or not response.content:
        return {"output": {"success": True}, "content_type": "application/json"}

    # Extract error message from Wix API response
    def extract_error(data):
        if isinstance(data, dict) and "message" in data:
            return data["message"]
        return "Wix API error"

    return ResponseHandler.handle_json_response(response, extract_error)
