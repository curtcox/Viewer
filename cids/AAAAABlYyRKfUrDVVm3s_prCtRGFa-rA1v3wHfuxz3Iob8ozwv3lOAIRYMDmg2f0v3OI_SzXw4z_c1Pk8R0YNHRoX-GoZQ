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
        "auth": "bearer",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _extract_error_message(data: Dict[str, Any]) -> str:
    error = data.get("error", {}) if isinstance(data.get("error"), dict) else data.get("error")
    if isinstance(error, dict):
        return error.get("message", "Stripe API error")
    if isinstance(error, str):
        return error
    return "Stripe API error"


def _process_webhook(
    *,
    payload: str,
    stripe_signature: str,
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
            signature_header="Stripe-Signature",
            signature_algorithm="sha256",
            signature_prefix="v1=",
        )
    )

    return receiver.process_webhook(
        payload=payload.encode(),
        headers={"Stripe-Signature": stripe_signature},
        handler=lambda data: {"output": {"event": data}},
    )


def main(
    *,
    operation: str = "list_customers",
    customer_id: str = "",
    charge_id: str = "",
    email: str = "",
    name: str = "",
    description: str = "",
    limit: int = 10,
    webhook_payload: str = "",
    stripe_signature: str = "",
    STRIPE_API_KEY: str = "",
    STRIPE_WEBHOOK_SECRET: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Stripe customers and charges or validate webhooks."""

    normalized_operation = operation.lower()

    if normalized_operation not in {
        "list_customers",
        "get_customer",
        "create_customer",
        "list_charges",
        "get_charge",
        "process_webhook",
    }:
        return validation_error("Unsupported operation", field="operation")

    if normalized_operation == "process_webhook":
        if not STRIPE_WEBHOOK_SECRET:
            return error_output(
                "Missing STRIPE_WEBHOOK_SECRET",
                status_code=401,
                details="Provide the signing secret used to validate webhook signatures.",
            )
        if not webhook_payload:
            return validation_error("Missing webhook_payload", field="webhook_payload")
        if not stripe_signature:
            return validation_error("Missing stripe_signature", field="stripe_signature")

        return _process_webhook(
            payload=webhook_payload,
            stripe_signature=stripe_signature,
            webhook_secret=STRIPE_WEBHOOK_SECRET,
            dry_run=dry_run,
        )

    if not STRIPE_API_KEY:
        return error_output(
            "Missing STRIPE_API_KEY",
            status_code=401,
            details="Provide a Stripe secret key to authenticate API calls.",
        )

    if normalized_operation == "create_customer" and not email:
        return validation_error("Missing required email", field="email")
    if normalized_operation == "get_customer" and not customer_id:
        return validation_error("Missing required customer_id", field="customer_id")
    if normalized_operation == "get_charge" and not charge_id:
        return validation_error("Missing required charge_id", field="charge_id")

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Authorization": f"Bearer {STRIPE_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    base_url = "https://api.stripe.com/v1"
    url = f"{base_url}/customers"
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_customers":
        params = {"limit": limit}
        if email:
            params["email"] = email
    elif normalized_operation == "get_customer":
        url = f"{base_url}/customers/{customer_id}"
    elif normalized_operation == "create_customer":
        method = "POST"
        payload = {"email": email}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
    elif normalized_operation == "list_charges":
        url = f"{base_url}/charges"
        params = {"limit": limit}
    elif normalized_operation == "get_charge":
        url = f"{base_url}/charges/{charge_id}"

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
            response = api_client.post(url, headers=headers, data=payload, timeout=timeout)
        else:
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Stripe request failed", status_code=status, details=str(exc))

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
