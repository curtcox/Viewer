# ruff: noqa: F821, F706
from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    WebhookConfig,
    WebhookReceiver,
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
        "auth": "custom_app_token",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _extract_error_message(data: Dict[str, Any]) -> str:
    errors = data.get("errors")
    if isinstance(errors, dict):
        return str(errors)
    if isinstance(errors, str):
        return errors
    if isinstance(errors, list) and errors:
        return str(errors[0])
    return "Shopify API error"


def _process_webhook(
    *,
    payload: str,
    hmac_header: str,
    webhook_secret: str,
    dry_run: bool,
) -> Dict[str, Any]:
    if dry_run:
        return {
            "output": {
                "preview": {
                    "operation": "process_webhook",
                    "message": "Dry run - webhook not validated",
                    "payload": payload,
                }
            }
        }

    receiver = WebhookReceiver(
        WebhookConfig(
            secret=webhook_secret,
            signature_header="X-Shopify-Hmac-SHA256",
            signature_algorithm="sha256",
            signature_prefix="",
        )
    )

    return receiver.process_webhook(
        payload=payload.encode(),
        headers={"X-Shopify-Hmac-SHA256": hmac_header},
        handler=lambda data: {"output": {"event": data}},
    )


def main(
    *,
    operation: str = "list_products",
    product_id: str = "",
    order_id: str = "",
    customer_id: str = "",
    title: str = "",
    body_html: str = "",
    vendor: str = "",
    product_type: str = "",
    price: str = "",
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    limit: int = 10,
    webhook_payload: str = "",
    hmac_header: str = "",
    SHOPIFY_ACCESS_TOKEN: str = "",
    SHOPIFY_STORE_URL: str = "",
    SHOPIFY_WEBHOOK_SECRET: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Shopify products, orders, customers or validate webhooks."""

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
        "process_webhook",
    }:
        return validation_error("Unsupported operation", field="operation")

    if normalized_operation == "process_webhook":
        if not SHOPIFY_WEBHOOK_SECRET:
            return error_output(
                "Missing SHOPIFY_WEBHOOK_SECRET",
                status_code=401,
                details="Provide the webhook secret used to validate HMAC signatures.",
            )
        if not webhook_payload:
            return validation_error("Missing webhook_payload", field="webhook_payload")
        if not hmac_header:
            return validation_error("Missing hmac_header", field="hmac_header")

        return _process_webhook(
            payload=webhook_payload,
            hmac_header=hmac_header,
            webhook_secret=SHOPIFY_WEBHOOK_SECRET,
            dry_run=dry_run,
        )

    if not SHOPIFY_ACCESS_TOKEN:
        return error_output(
            "Missing SHOPIFY_ACCESS_TOKEN",
            status_code=401,
            details="Provide a Shopify Admin API access token.",
        )

    if not SHOPIFY_STORE_URL:
        return error_output(
            "Missing SHOPIFY_STORE_URL",
            status_code=401,
            details="Provide your Shopify store URL (e.g., 'mystore.myshopify.com').",
        )

    # Normalize store URL
    store_url = SHOPIFY_STORE_URL.replace("https://", "").replace("http://", "").strip("/")

    if normalized_operation == "create_product" and not title:
        return validation_error("Missing required title", field="title")
    if normalized_operation == "get_product" and not product_id:
        return validation_error("Missing required product_id", field="product_id")
    if normalized_operation == "get_order" and not order_id:
        return validation_error("Missing required order_id", field="order_id")
    if normalized_operation == "get_customer" and not customer_id:
        return validation_error("Missing required customer_id", field="customer_id")
    if normalized_operation == "create_customer" and not email:
        return validation_error("Missing required email", field="email")

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{store_url}/admin/api/2024-01"
    url = f"{base_url}/products.json"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_products":
        params = {"limit": limit}
    elif normalized_operation == "get_product":
        url = f"{base_url}/products/{product_id}.json"
    elif normalized_operation == "create_product":
        method = "POST"
        product_data: Dict[str, Any] = {"title": title}
        if body_html:
            product_data["body_html"] = body_html
        if vendor:
            product_data["vendor"] = vendor
        if product_type:
            product_data["product_type"] = product_type
        if price:
            product_data["variants"] = [{"price": price}]
        payload = {"product": product_data}
    elif normalized_operation == "list_orders":
        url = f"{base_url}/orders.json"
        params = {"limit": limit}
    elif normalized_operation == "get_order":
        url = f"{base_url}/orders/{order_id}.json"
    elif normalized_operation == "list_customers":
        url = f"{base_url}/customers.json"
        params = {"limit": limit}
    elif normalized_operation == "get_customer":
        url = f"{base_url}/customers/{customer_id}.json"
    elif normalized_operation == "create_customer":
        method = "POST"
        url = f"{base_url}/customers.json"
        customer_data: Dict[str, Any] = {"email": email}
        if first_name:
            customer_data["first_name"] = first_name
        if last_name:
            customer_data["last_name"] = last_name
        payload = {"customer": customer_data}

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
        return error_output("Shopify request failed", status_code=status, details=str(exc))

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
