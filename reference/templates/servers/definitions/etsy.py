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
    error = data.get("error", "")
    if error:
        return error
    message = data.get("message", "")
    if message:
        return message
    return "Etsy API error"


def main(
    *,
    operation: str = "list_shops",
    shop_id: str = "",
    listing_id: str = "",
    title: str = "",
    description: str = "",
    price: str = "",
    quantity: int = 1,
    who_made: str = "i_did",
    when_made: str = "made_to_order",
    limit: int = 10,
    ETSY_ACCESS_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Etsy shops and listings."""

    normalized_operation = operation.lower()

    if normalized_operation not in {
        "list_shops",
        "get_shop",
        "list_listings",
        "get_listing",
        "create_listing",
        "update_listing",
    }:
        return validation_error("Unsupported operation", field="operation")

    if not ETSY_ACCESS_TOKEN:
        return error_output(
            "Missing ETSY_ACCESS_TOKEN",
            status_code=401,
            details="Provide an Etsy OAuth access token.",
        )

    if normalized_operation == "get_shop" and not shop_id:
        return validation_error("Missing required shop_id", field="shop_id")
    if normalized_operation == "list_listings" and not shop_id:
        return validation_error("Missing required shop_id", field="shop_id")
    if normalized_operation in {"get_listing", "update_listing"} and not listing_id:
        return validation_error("Missing required listing_id", field="listing_id")
    if normalized_operation == "create_listing":
        if not shop_id:
            return validation_error("Missing required shop_id", field="shop_id")
        if not title:
            return validation_error("Missing required title", field="title")
        if not price:
            return validation_error("Missing required price", field="price")

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": ETSY_ACCESS_TOKEN,  # Etsy also requires this header
    }

    base_url = "https://openapi.etsy.com/v3/application"
    url = f"{base_url}/shops"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_shops":
        params = {"limit": limit}
    elif normalized_operation == "get_shop":
        url = f"{base_url}/shops/{shop_id}"
    elif normalized_operation == "list_listings":
        url = f"{base_url}/shops/{shop_id}/listings/active"
        params = {"limit": limit}
    elif normalized_operation == "get_listing":
        url = f"{base_url}/listings/{listing_id}"
    elif normalized_operation == "create_listing":
        method = "POST"
        url = f"{base_url}/shops/{shop_id}/listings"
        listing_data: Dict[str, Any] = {
            "title": title,
            "quantity": quantity,
            "price": price,
            "who_made": who_made,
            "when_made": when_made,
        }
        if description:
            listing_data["description"] = description
        payload = listing_data
    elif normalized_operation == "update_listing":
        method = "PUT"
        url = f"{base_url}/listings/{listing_id}"
        listing_data = {}
        if title:
            listing_data["title"] = title
        if description:
            listing_data["description"] = description
        if price:
            listing_data["price"] = price
        if quantity:
            listing_data["quantity"] = quantity
        payload = listing_data

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
        elif method == "PUT":
            response = api_client.put(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Etsy request failed", status_code=status, details=str(exc))

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
