# ruff: noqa: F821, F706
"""Interact with Squarespace to manage products, orders, and inventory."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    PreviewBuilder,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()
_BASE_URL = "https://api.squarespace.com/1.0"


def _build_create_product_payload(
    *,
    name: str,
    price: float | None,
    description: str,
    sku: str,
    **_: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": name,
        "variants": [
            {
                "pricing": {
                    "basePrice": {
                        "currency": "USD",
                        "value": str(price),
                    }
                },
                "sku": sku if sku else None,
            }
        ],
    }
    if description:
        payload["description"] = description
    return payload


def _build_update_product_payload(
    *,
    name: str,
    description: str,
    price: float | None,
    **_: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
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
                        "value": str(price),
                    }
                }
            }
        ]
    return payload


_OPERATIONS = {
    "list_products": OperationDefinition(),
    "get_product": OperationDefinition(required=(RequiredField("product_id"),)),
    "create_product": OperationDefinition(
        required=(RequiredField("name"), RequiredField("price")),
        payload_builder=_build_create_product_payload,
    ),
    "update_product": OperationDefinition(
        required=(RequiredField("product_id"),),
        payload_builder=_build_update_product_payload,
    ),
    "delete_product": OperationDefinition(required=(RequiredField("product_id"),)),
    "list_orders": OperationDefinition(),
    "get_order": OperationDefinition(required=(RequiredField("order_id"),)),
    "list_inventory": OperationDefinition(),
    "get_inventory": OperationDefinition(required=(RequiredField("inventory_item_id"),)),
    "update_inventory": OperationDefinition(
        required=(RequiredField("inventory_item_id"), RequiredField("quantity")),
        payload_builder=lambda quantity, **_: {"quantity": quantity},
    ),
}

_METHODS = {
    "create_product": "POST",
    "update_product": "PUT",
    "delete_product": "DELETE",
    "update_inventory": "PUT",
}

_ENDPOINT_BUILDERS = {
    "list_products": lambda base_url, **_: f"{base_url}/commerce/products",
    "get_product": lambda base_url, product_id, **_: f"{base_url}/commerce/products/{product_id}",
    "create_product": lambda base_url, **_: f"{base_url}/commerce/products",
    "update_product": lambda base_url, product_id, **_: f"{base_url}/commerce/products/{product_id}",
    "delete_product": lambda base_url, product_id, **_: f"{base_url}/commerce/products/{product_id}",
    "list_orders": lambda base_url, **_: f"{base_url}/commerce/orders",
    "get_order": lambda base_url, order_id, **_: f"{base_url}/commerce/orders/{order_id}",
    "list_inventory": lambda base_url, **_: f"{base_url}/commerce/inventory",
    "get_inventory": lambda base_url, inventory_item_id, **_: (
        f"{base_url}/commerce/inventory/{inventory_item_id}"
    ),
    "update_inventory": lambda base_url, inventory_item_id, **_: (
        f"{base_url}/commerce/inventory/{inventory_item_id}"
    ),
}

_LIST_OPERATIONS = {"list_products", "list_orders", "list_inventory"}


def _build_list_params(cursor: str, limit: int) -> Dict[str, Any] | None:
    params: Dict[str, Any] = {}
    if cursor:
        params["cursor"] = cursor
    if limit:
        params["limit"] = min(limit, 200)
    return params or None


def _build_params(operation: str, cursor: str, limit: int) -> Dict[str, Any] | None:
    if operation in _LIST_OPERATIONS:
        return _build_list_params(cursor, limit)
    return None


def _extract_error(response: object, data: object) -> str:
    if isinstance(data, dict):
        return data.get("message", "Squarespace API error")
    return "Squarespace API error"


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

    payload_result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        product_id=product_id,
        order_id=order_id,
        inventory_item_id=inventory_item_id,
        name=name,
        price=price,
        quantity=quantity,
        description=description,
        sku=sku,
    )
    if isinstance(payload_result, tuple):
        return validation_error(payload_result[0], field=payload_result[1])
    payload = payload_result or None
    if isinstance(payload, dict) and not payload:
        payload = None

    if not SQUARESPACE_API_KEY:
        return error_output("Missing SQUARESPACE_API_KEY", status_code=401)

    params = _build_params(operation, cursor, limit)
    endpoint_builder = _ENDPOINT_BUILDERS.get(operation)
    if not endpoint_builder:
        return validation_error("Unsupported operation", field="operation")
    url = endpoint_builder(
        _BASE_URL,
        product_id=product_id,
        order_id=order_id,
        inventory_item_id=inventory_item_id,
    )
    method = _METHODS.get(operation, "GET")

    # Dry-run preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=operation,
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

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_extract_error,
        empty_response_statuses=(204,),
        empty_response_output={"success": True},
    )
