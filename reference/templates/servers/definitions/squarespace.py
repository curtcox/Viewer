# ruff: noqa: F821, F706
"""Interact with Squarespace to manage products, orders, and inventory."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    product_id: Optional[str],
    order_id: Optional[str],
    inventory_item_id: Optional[str],
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base_url = "https://api.squarespace.com/1.0"

    if operation == "list_products":
        url = f"{base_url}/commerce/products"
        method = "GET"
    elif operation == "get_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "GET"
    elif operation == "create_product":
        url = f"{base_url}/commerce/products"
        method = "POST"
    elif operation == "update_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "PUT"
    elif operation == "delete_product":
        url = f"{base_url}/commerce/products/{product_id}"
        method = "DELETE"
    elif operation == "list_orders":
        url = f"{base_url}/commerce/orders"
        method = "GET"
    elif operation == "get_order":
        url = f"{base_url}/commerce/orders/{order_id}"
        method = "GET"
    elif operation == "list_inventory":
        url = f"{base_url}/commerce/inventory"
        method = "GET"
    elif operation == "get_inventory":
        url = f"{base_url}/commerce/inventory/{inventory_item_id}"
        method = "GET"
    elif operation == "update_inventory":
        url = f"{base_url}/commerce/inventory/{inventory_item_id}"
        method = "PUT"
    else:
        url = base_url
        method = "GET"

    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Bearer token",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


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

    normalized_operation = operation.lower()
    valid_operations = {
        "list_products", "get_product", "create_product", "update_product", "delete_product",
        "list_orders", "get_order",
        "list_inventory", "get_inventory", "update_inventory"
    }

    if normalized_operation not in valid_operations:
        return validation_error(
            f"Unsupported operation: {operation}. Must be one of {', '.join(sorted(valid_operations))}",
            field="operation"
        )

    # Validate required parameters based on operation
    if normalized_operation in {"get_product", "update_product", "delete_product"} and not product_id:
        return validation_error(f"Missing required product_id for {normalized_operation}", field="product_id")

    if normalized_operation == "get_order" and not order_id:
        return validation_error("Missing required order_id", field="order_id")

    if normalized_operation in {"get_inventory", "update_inventory"} and not inventory_item_id:
        return validation_error(f"Missing required inventory_item_id for {normalized_operation}", field="inventory_item_id")

    if normalized_operation == "create_product" and not name:
        return validation_error("Missing required name for create_product", field="name")

    if normalized_operation == "create_product" and price is None:
        return validation_error("Missing required price for create_product", field="price")

    if normalized_operation == "update_inventory" and quantity is None:
        return validation_error("Missing required quantity for update_inventory", field="quantity")

    if not SQUARESPACE_API_KEY:
        return error_output(
            "Missing SQUARESPACE_API_KEY. Get your API key from Squarespace Settings > Advanced > API Keys",
            status_code=401
        )

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
        payload = {
            "quantity": quantity
        }
    elif normalized_operation in {"list_products", "list_orders", "list_inventory"}:
        params = {}
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = min(limit, 200)  # Max 200

    # Dry-run preview
    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            product_id=product_id,
            order_id=order_id,
            inventory_item_id=inventory_item_id,
            payload=payload,
            params=params,
        )
        return {"output": {"dry_run": True, "preview": preview}, "content_type": "application/json"}

    # Make the actual API call
    api_client = client or _DEFAULT_CLIENT
    base_url = "https://api.squarespace.com/1.0"
    headers = {
        "Authorization": f"Bearer {SQUARESPACE_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Viewer/1.0",
    }

    # Build URL based on operation
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
        return validation_error(f"Unknown operation: {operation}")

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if payload else None,
            params=params if params else None,
            timeout=timeout,
        )

        if response.status_code == 401:
            return error_output(
                "Invalid or expired SQUARESPACE_API_KEY. Check your API key in Squarespace Settings",
                status_code=401
            )
        if response.status_code == 403:
            return error_output(
                "Insufficient permissions for this operation. Check your API key has the required scopes",
                status_code=403
            )
        if response.status_code == 404:
            return error_output(
                f"Resource not found (product_id={product_id}, order_id={order_id}, inventory_item_id={inventory_item_id})",
                status_code=404
            )

        response.raise_for_status()

        # Some operations return no content
        if response.status_code == 204 or not response.content:
            return {"output": {"success": True}, "content_type": "application/json"}

        try:
            data = response.json()
            return {"output": data, "content_type": "application/json"}
        except requests.exceptions.JSONDecodeError:
            return error_output(
                "Failed to parse API response as JSON",
                status_code=response.status_code,
                response=response.text[:500]
            )

    except requests.exceptions.Timeout:
        return error_output(
            f"Request timed out after {timeout} seconds. Try increasing the timeout parameter",
            status_code=408
        )
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else None
        error_detail = e.response.text[:500] if e.response else str(e)
        return error_output(
            f"Squarespace API request failed: {str(e)}",
            status_code=status_code,
            response=error_detail
        )
