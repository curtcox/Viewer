# ruff: noqa: F821, F706
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

_OPERATIONS = {
    "list_shops": OperationDefinition(),
    "get_shop": OperationDefinition(
        required=(RequiredField("shop_id"),),
    ),
    "list_listings": OperationDefinition(
        required=(RequiredField("shop_id"),),
    ),
    "get_listing": OperationDefinition(
        required=(RequiredField("listing_id"),),
    ),
    "create_listing": OperationDefinition(
        required=(RequiredField("shop_id"), RequiredField("title"), RequiredField("price")),
        payload_builder=lambda title, description, price, quantity, who_made, when_made, **_: {
            "title": title,
            "quantity": quantity,
            "price": price,
            "who_made": who_made,
            "when_made": when_made,
            **({"description": description} if description else {}),
        },
    ),
    "update_listing": OperationDefinition(
        required=(RequiredField("listing_id"),),
        payload_builder=lambda title, description, price, quantity, **_: {
            **({"title": title} if title else {}),
            **({"description": description} if description else {}),
            **({"price": price} if price else {}),
            **({"quantity": quantity} if quantity else {}),
        },
    ),
}

_ENDPOINT_BUILDERS = {
    "list_shops": lambda **_: "shops",
    "get_shop": lambda shop_id, **_: f"shops/{shop_id}",
    "list_listings": lambda shop_id, **_: f"shops/{shop_id}/listings/active",
    "get_listing": lambda listing_id, **_: f"listings/{listing_id}",
    "create_listing": lambda shop_id, **_: f"shops/{shop_id}/listings",
    "update_listing": lambda listing_id, **_: f"listings/{listing_id}",
}

_METHODS = {
    "create_listing": "POST",
    "update_listing": "PUT",
}

_PARAMETER_BUILDERS = {
    "list_shops": lambda limit, **_: {"limit": limit},
    "list_listings": lambda limit, **_: {"limit": limit},
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


def _etsy_error_message(_response: Any, data: Any) -> str:
    if isinstance(data, dict):
        return _extract_error_message(data)
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

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not ETSY_ACCESS_TOKEN:
        return error_output(
            "Missing ETSY_ACCESS_TOKEN",
            status_code=401,
            details="Provide an Etsy OAuth access token.",
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        shop_id=shop_id,
        listing_id=listing_id,
        title=title,
        description=description,
        price=price,
        quantity=quantity,
        who_made=who_made,
        when_made=when_made,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": ETSY_ACCESS_TOKEN,  # Etsy also requires this header
    }

    base_url = "https://openapi.etsy.com/v3/application"
    endpoint = _ENDPOINT_BUILDERS[operation](shop_id=shop_id, listing_id=listing_id)
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

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_etsy_error_message,
        request_error_message="Etsy request failed",
    )
