# ruff: noqa: F821, F706
"""Interact with Squarespace to manage products, orders, and inventory."""

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


_DEFAULT_CLIENT = ExternalApiClient()
_OPERATIONS = {
    "list_products", "get_product", "create_product", "update_product", "delete_product",
    "list_orders", "get_order",
    "list_inventory", "get_inventory", "update_inventory"
}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "get_product": ["product_id"],
    "update_product": ["product_id"],
    "delete_product": ["product_id"],
    "get_order": ["order_id"],
    "get_inventory": ["inventory_item_id"],
    "update_inventory": ["inventory_item_id", "quantity"],
    "create_product": ["name", "price"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


def main(
    *,
    operation: str = "list_products",
    product_id: str = "",
    order_id: str = "",
    inventory_item_id: str = "",
    name: str = "",
    description: str = "",
    price: Optional[float] = None,
    quantity: Optional[int] = None,
    sku: str = "",
    cursor: str = "",
    limit: int = 20,
    SQUARESPACE_API_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Manage products, orders, and inventory in Squarespace Commerce.

    Operations:
    - list_products: List all products (supports pagination with cursor and limit)
    - get_product: Get product details (requires product_id)
    - create_product: Create a new product (requires name and price)
    - update_product: Update a product (requires product_id)
    - delete_product: Delete a product (requires product_id)
    - list_orders: List all orders (supports pagination)
    - get_order: Get order details (requires order_id)
    - list_inventory: List all inventory items (supports pagination)
    - get_inventory: Get inventory details (requires inventory_item_id)
    - update_inventory: Update inventory quantity (requires inventory_item_id and quantity)

    Args:
        operation: The operation to perform
        product_id: The product ID for get/update/delete operations
        order_id: The order ID for get operation
        inventory_item_id: The inventory item ID for get/update operations
        name: Product name for create/update operations
        description: Product description for create/update operations
        price: Product price for create/update operations
        quantity: Inventory quantity for update_inventory operation
        sku: Product SKU for create/update operations
        cursor: Pagination cursor for list operations
        limit: Number of items to return (max 200)
        SQUARESPACE_API_KEY: Squarespace API key from account settings
        dry_run: If True, return preview without making actual API call
        timeout: Request timeout in seconds
        client: Optional ExternalApiClient for testing
        context: Request context
    """

    # Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Validate credentials
    if error := CredentialValidator.require_secret(SQUARESPACE_API_KEY, "SQUARESPACE_API_KEY"):
        return error

    # Validate operation-specific parameters
    # Note: price and quantity are special as they can be None vs empty string
    params_dict = {
        "product_id": product_id,
        "order_id": order_id,
        "inventory_item_id": inventory_item_id,
        "name": name,
        "price": price,
        "quantity": quantity,
    }
    if error := _PARAMETER_VALIDATOR.validate_required(normalized_operation, params_dict):
        return error

    # Build payload for create/update operations
    payload = None
    params = None

    if normalized_operation == "create_product":
        payload = {
            "name": name,
            "variants": [
                {
                    "pricing": {
                        "basePrice": {
                            "currency": "USD",
                            "value": str(price)
                        }
                    },
                    "sku": sku if sku else None,
                }
            ]
        }
        if description:
            payload["description"] = description
    elif normalized_operation == "update_product":
        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if price is not None:
            payload["variants"] = [
                {
                    "pricing": {
                        "basePrice": {
                            "currency": "USD",
                            "value": str(price)
                        }
                    }
                }
            ]
    elif normalized_operation == "update_inventory":
        payload = {"quantity": quantity}
    elif normalized_operation in {"list_products", "list_orders", "list_inventory"}:
        params = {}
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = min(limit, 200)  # Max 200

    # Build URL based on operation
    base_url = "https://api.squarespace.com/1.0"
    if normalized_operation == "list_products":
        url = f"{base_url}/commerce/products"
        method = "GET"
    elif normalized_operation == "get_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "GET"
    elif normalized_operation == "create_product":
        url = f"{base_url}/commerce/products"
        method = "POST"
    elif normalized_operation == "update_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "PUT"
    elif normalized_operation == "delete_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "DELETE"
    elif normalized_operation == "list_orders":
        url = f"{base_url}/commerce/orders"
        method = "GET"
    elif normalized_operation == "get_order":
        url = f"{base_url}/commerce/orders/{order_id}"
        method = "GET"
    elif normalized_operation == "list_inventory":
        url = f"{base_url}/commerce/inventory"
        method = "GET"
    elif normalized_operation == "get_inventory":
        url = f"{base_url}/commerce/inventory/{inventory_item_id}"
        method = "GET"
    elif normalized_operation == "update_inventory":
        url = f"{base_url}/commerce/inventory/{inventory_item_id}"
        method = "PUT"
    else:
        url = base_url
        method = "GET"

    # Dry-run preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    # Make the actual API call
    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {SQUARESPACE_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Viewer/1.0",
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

    # Some operations return no content (204)
    if response.status_code == 204 or not response.content:
        return {"output": {"success": True}, "content_type": "application/json"}

    # Extract error message from Squarespace API response
    def extract_error(data: Dict[str, Any]) -> str:
        if isinstance(data, dict):
            return data.get("message", "Squarespace API error")
        return "Squarespace API error"

    return ResponseHandler.handle_json_response(response, extract_error)
