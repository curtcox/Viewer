# ruff: noqa: F821, F706
from __future__ import annotations

from typing import Any, Dict, Optional
import base64

import requests

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

_OPERATIONS = {
    "list_products": OperationDefinition(),
    "get_product": OperationDefinition(
        required=(RequiredField("product_id"),),
    ),
    "create_product": OperationDefinition(
        required=(RequiredField("name"),),
        payload_builder=lambda name, regular_price, **_: {
            "name": name,
            **({"regular_price": regular_price} if regular_price else {}),
        },
    ),
    "list_orders": OperationDefinition(),
    "get_order": OperationDefinition(
        required=(RequiredField("order_id"),),
    ),
    "list_customers": OperationDefinition(),
    "get_customer": OperationDefinition(
        required=(RequiredField("customer_id"),),
    ),
    "create_customer": OperationDefinition(
        required=(RequiredField("email"),),
        payload_builder=lambda email, first_name, last_name, **_: {
            "email": email,
            **({"first_name": first_name} if first_name else {}),
            **({"last_name": last_name} if last_name else {}),
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_products": lambda **_: "products",
    "get_product": lambda product_id, **_: f"products/{product_id}",
    "create_product": lambda **_: "products",
    "list_orders": lambda **_: "orders",
    "get_order": lambda order_id, **_: f"orders/{order_id}",
    "list_customers": lambda **_: "customers",
    "get_customer": lambda customer_id, **_: f"customers/{customer_id}",
    "create_customer": lambda **_: "customers",
}

_METHODS = {
    "create_product": "POST",
    "create_customer": "POST",
}

_PARAMETER_BUILDERS = {
    "list_products": lambda limit, **_: {"per_page": limit},
    "list_orders": lambda limit, **_: {"per_page": limit},
    "list_customers": lambda limit, **_: {"per_page": limit},
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


def _extract_error_message(data: Dict[str, Any]) -> str:
    message = data.get("message", "")
    if message:
        return message
    code = data.get("code", "")
    if code:
        return f"WooCommerce API error: {code}"
    return "WooCommerce API error"


def _woocommerce_error_message(_response: requests.Response, data: Any) -> str:
    if isinstance(data, dict):
        return _extract_error_message(data)
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

    if operation not in _OPERATIONS:
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

    store_url = WOOCOMMERCE_STORE_URL.rstrip("/")
    if not store_url.startswith("http"):
        store_url = f"https://{store_url}"

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        product_id=product_id,
        order_id=order_id,
        customer_id=customer_id,
        name=name,
        regular_price=regular_price,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    endpoint = _ENDPOINT_BUILDERS[operation](
        product_id=product_id,
        order_id=order_id,
        customer_id=customer_id,
    )
    base_url = f"{store_url}/wp-json/wc/v3"
    url = f"{base_url}/{endpoint}"
    method = _METHODS.get(operation, "GET")
    params = _PARAMETER_BUILDERS.get(operation, lambda **_: None)(limit=limit)
    payload = result if isinstance(result, dict) else None

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    credentials = f"{WOOCOMMERCE_CONSUMER_KEY}:{WOOCOMMERCE_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_woocommerce_error_message,
        request_error_message="WooCommerce request failed",
        include_exception_in_message=False,
    )
