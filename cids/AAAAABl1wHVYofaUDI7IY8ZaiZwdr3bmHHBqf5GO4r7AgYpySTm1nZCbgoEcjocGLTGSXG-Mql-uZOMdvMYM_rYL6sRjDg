# ruff: noqa: F821, F706
from __future__ import annotations

from typing import Any, Dict, Optional
import base64

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
        "auth": "basic",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _extract_error_message(data: Dict[str, Any]) -> str:
    message = data.get("message", "")
    if message:
        return message
    code = data.get("code", "")
    if code:
        return f"WooCommerce API error: {code}"
    return "WooCommerce API error"


def main(
    *,
    operation: str = "list_products",
    product_id: str = "",
    order_id: str = "",
    customer_id: str = "",
    name: str = "",
    regular_price: str = "",
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    limit: int = 10,
    WOOCOMMERCE_CONSUMER_KEY: str = "",
    WOOCOMMERCE_CONSUMER_SECRET: str = "",
    WOOCOMMERCE_STORE_URL: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with WooCommerce products, orders, and customers."""

    normalized_operation = operation.lower()

    if normalized_operation not in {
        "list_products",
        "get_product",
        "create_product",
        "list_orders",
        "get_order",
        "list_customers",
        "get_customer",
        "create_customer",
    }:
        return validation_error("Unsupported operation", field="operation")

    if not WOOCOMMERCE_CONSUMER_KEY:
        return error_output(
            "Missing WOOCOMMERCE_CONSUMER_KEY",
            status_code=401,
            details="Provide a WooCommerce REST API consumer key.",
        )

    if not WOOCOMMERCE_CONSUMER_SECRET:
        return error_output(
            "Missing WOOCOMMERCE_CONSUMER_SECRET",
            status_code=401,
            details="Provide a WooCommerce REST API consumer secret.",
        )

    if not WOOCOMMERCE_STORE_URL:
        return error_output(
            "Missing WOOCOMMERCE_STORE_URL",
            status_code=401,
            details="Provide your WooCommerce store URL (e.g., 'https://mystore.com').",
        )

    # Normalize store URL
    store_url = WOOCOMMERCE_STORE_URL.rstrip("/")
    if not store_url.startswith("http"):
        store_url = f"https://{store_url}"

    if normalized_operation == "create_product" and not name:
        return validation_error("Missing required name", field="name")
    if normalized_operation == "get_product" and not product_id:
        return validation_error("Missing required product_id", field="product_id")
    if normalized_operation == "get_order" and not order_id:
        return validation_error("Missing required order_id", field="order_id")
    if normalized_operation == "get_customer" and not customer_id:
        return validation_error("Missing required customer_id", field="customer_id")
    if normalized_operation == "create_customer" and not email:
        return validation_error("Missing required email", field="email")

    # Create Basic Auth header
    credentials = f"{WOOCOMMERCE_CONSUMER_KEY}:{WOOCOMMERCE_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"{store_url}/wp-json/wc/v3"
    url = f"{base_url}/products"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_products":
        params = {"per_page": limit}
    elif normalized_operation == "get_product":
        url = f"{base_url}/products/{product_id}"
    elif normalized_operation == "create_product":
        method = "POST"
        product_data: Dict[str, Any] = {"name": name}
        if regular_price:
            product_data["regular_price"] = regular_price
        payload = product_data
    elif normalized_operation == "list_orders":
        url = f"{base_url}/orders"
        params = {"per_page": limit}
    elif normalized_operation == "get_order":
        url = f"{base_url}/orders/{order_id}"
    elif normalized_operation == "list_customers":
        url = f"{base_url}/customers"
        params = {"per_page": limit}
    elif normalized_operation == "get_customer":
        url = f"{base_url}/customers/{customer_id}"
    elif normalized_operation == "create_customer":
        method = "POST"
        url = f"{base_url}/customers"
        customer_data: Dict[str, Any] = {"email": email}
        if first_name:
            customer_data["first_name"] = first_name
        if last_name:
            customer_data["last_name"] = last_name
        payload = customer_data

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
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("WooCommerce request failed", status_code=status, details=str(exc))

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
