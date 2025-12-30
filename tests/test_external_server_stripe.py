from __future__ import annotations

import hashlib
import hmac
import json
import time

import requests

from reference_templates.servers.definitions import stripe


class DummyResponse:
    def __init__(self, status_code: int, json_data, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FakeClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_api_key_for_api_operations():
    result = stripe.main()

    assert result["output"]["error"] == "Missing STRIPE_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = stripe.main(operation="unknown", STRIPE_API_KEY="key")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_customer_requires_email():
    result = stripe.main(operation="create_customer", STRIPE_API_KEY="key")

    assert result["output"]["error"]["message"] == "Missing required email"


def test_get_customer_requires_id():
    result = stripe.main(operation="get_customer", STRIPE_API_KEY="key")

    assert result["output"]["error"]["message"] == "Missing required customer_id"


def test_dry_run_preview_for_list_customers():
    result = stripe.main(STRIPE_API_KEY="key", limit=5, email="user@example.com")

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_customers"
    assert preview["params"] == {"limit": 5, "email": "user@example.com"}


def test_dry_run_preview_for_create_customer():
    result = stripe.main(
        operation="create_customer",
        STRIPE_API_KEY="key",
        email="test@example.com",
        name="Test User",
        description="Customer note",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["payload"] == {
        "email": "test@example.com",
        "name": "Test User",
        "description": "Customer note",
    }


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = stripe.main(STRIPE_API_KEY="key", dry_run=False, client=client)

    assert result["output"]["error"] == "Stripe request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = stripe.main(STRIPE_API_KEY="key", dry_run=False, client=client)

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_uses_stripe_message():
    response = DummyResponse(status_code=402, json_data={"error": {"message": "Card declined"}})
    client = FakeClient(response=response)

    result = stripe.main(STRIPE_API_KEY="key", dry_run=False, client=client)

    assert result["output"]["error"] == "Card declined"
    assert result["output"]["status_code"] == 402
    assert result["output"]["response"] == {"error": {"message": "Card declined"}}


def test_success_returns_payload():
    payload = {"data": [{"id": "cus_123"}]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = stripe.main(STRIPE_API_KEY="key", dry_run=False, client=client)

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
    assert "/customers" in client.calls[0][1]


def test_process_webhook_valid_signature():
    payload = json.dumps({"id": "evt_123", "type": "customer.created"})
    secret = "whsec_test"
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode() + payload.encode()
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    result = stripe.main(
        operation="process_webhook",
        STRIPE_WEBHOOK_SECRET=secret,
        webhook_payload=payload,
        stripe_signature=f"t={timestamp},v1={signature}",
        dry_run=False,
    )

    assert result["output"]["event"]["id"] == "evt_123"


def test_process_webhook_invalid_signature():
    payload = json.dumps({"id": "evt_123", "type": "customer.created"})
    secret = "whsec_test"
    timestamp = int(time.time())

    result = stripe.main(
        operation="process_webhook",
        STRIPE_WEBHOOK_SECRET=secret,
        webhook_payload=payload,
        stripe_signature=f"t={timestamp},v1=invalid",
        dry_run=False,
    )

    assert result["output"]["error"]["message"] == "Invalid webhook signature"
    assert result["output"]["error"]["status_code"] == 401
