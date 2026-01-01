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
        "auth": "oauth",
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
    details = data.get("details", [])
    if isinstance(details, list) and details:
        detail = details[0]
        if isinstance(detail, dict):
            return detail.get("issue", "PayPal API error")
    name = data.get("name", "")
    if name:
        return f"PayPal error: {name}"
    return "PayPal API error"


def _get_access_token(
    client_id: str,
    client_secret: str,
    sandbox: bool,
    api_client: ExternalApiClient,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Get OAuth access token from PayPal."""
    base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"
    token_url = f"{base_url}/v1/oauth2/token"

    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    try:
        response = api_client.post(token_url, headers=headers, data=data, timeout=30)
        if not getattr(response, "ok", False):
            return None, error_output(
                "Failed to obtain PayPal access token",
                status_code=response.status_code,
                details=response.text[:500] if hasattr(response, "text") else None,
            )
        token_data = response.json()
        return token_data.get("access_token"), None
    except Exception as exc:
        return None, error_output(
            "Failed to obtain PayPal access token",
            details=str(exc),
        )


def main(
    *,
    operation: str = "create_order",
    order_id: str = "",
    payment_id: str = "",
    amount: str = "",
    currency_code: str = "USD",
    return_url: str = "",
    cancel_url: str = "",
    description: str = "",
    start_date: str = "",
    end_date: str = "",
    sandbox: bool = True,
    PAYPAL_CLIENT_ID: str = "",
    PAYPAL_CLIENT_SECRET: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with PayPal orders and payments."""

    normalized_operation = operation.lower()

    if normalized_operation not in {
        "create_order",
        "get_order",
        "capture_payment",
        "list_transactions",
    }:
        return validation_error("Unsupported operation", field="operation")

    if not PAYPAL_CLIENT_ID:
        return error_output(
            "Missing PAYPAL_CLIENT_ID",
            status_code=401,
            details="Provide a PayPal REST API client ID.",
        )

    if not PAYPAL_CLIENT_SECRET:
        return error_output(
            "Missing PAYPAL_CLIENT_SECRET",
            status_code=401,
            details="Provide a PayPal REST API client secret.",
        )

    if normalized_operation == "create_order" and not amount:
        return validation_error("Missing required amount", field="amount")
    if normalized_operation in {"get_order", "capture_payment"} and not order_id:
        return validation_error("Missing required order_id", field="order_id")
    if normalized_operation == "list_transactions":
        if not start_date:
            return validation_error("Missing required start_date", field="start_date")
        if not end_date:
            return validation_error("Missing required end_date", field="end_date")

    api_client = client or _DEFAULT_CLIENT

    # Get access token if not in dry run mode
    access_token = None
    if not dry_run:
        access_token, error = _get_access_token(
            PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, sandbox, api_client
        )
        if error:
            return error

    base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"
    url = f"{base_url}/v2/checkout/orders"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "create_order":
        method = "POST"
        order_data: Dict[str, Any] = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency_code,
                        "value": amount,
                    }
                }
            ],
        }
        if description:
            order_data["purchase_units"][0]["description"] = description
        if return_url and cancel_url:
            order_data["application_context"] = {
                "return_url": return_url,
                "cancel_url": cancel_url,
            }
        payload = order_data
    elif normalized_operation == "get_order":
        url = f"{base_url}/v2/checkout/orders/{order_id}"
    elif normalized_operation == "capture_payment":
        method = "POST"
        url = f"{base_url}/v2/checkout/orders/{order_id}/capture"
    elif normalized_operation == "list_transactions":
        url = f"{base_url}/v1/reporting/transactions"
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        if method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("PayPal request failed", status_code=status, details=str(exc))

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
