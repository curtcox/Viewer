from __future__ import annotations

import requests

from reference_templates.servers.definitions import paypal


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


def test_requires_client_id():
    result = paypal.main(PAYPAL_CLIENT_SECRET="secret")

    assert result["output"]["error"] == "Missing PAYPAL_CLIENT_ID"
    assert result["output"]["status_code"] == 401


def test_requires_client_secret():
    result = paypal.main(PAYPAL_CLIENT_ID="client_id")

    assert result["output"]["error"] == "Missing PAYPAL_CLIENT_SECRET"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = paypal.main(
        operation="unknown",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_order_requires_amount():
    result = paypal.main(
        operation="create_order",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required amount"


def test_get_order_requires_order_id():
    result = paypal.main(
        operation="get_order",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required order_id"


def test_list_transactions_requires_dates():
    result = paypal.main(
        operation="list_transactions",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required start_date"


def test_dry_run_preview_for_create_order():
    result = paypal.main(
        operation="create_order",
        amount="100.00",
        currency_code="USD",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_order"
    assert preview["payload"]["purchase_units"][0]["amount"]["value"] == "100.00"


def test_dry_run_preview_for_get_order():
    result = paypal.main(
        operation="get_order",
        order_id="ORDER123",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "get_order"
    assert "ORDER123" in preview["url"]


def test_create_order_success():
    # Mock both token request and order creation
    fake_client = FakeClient(
        response=DummyResponse(200, {"access_token": "token123"})
    )

    paypal.main(
        operation="create_order",
        amount="50.00",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        dry_run=False,
        client=fake_client,
    )

    # Token call happens first, then order creation (but order creation will also get token response)
    assert len(fake_client.calls) == 2
    assert fake_client.calls[0][0] == "POST"  # Token request
    assert fake_client.calls[1][0] == "POST"  # Order creation


def test_get_order_with_token_success():
    fake_client = FakeClient(
        response=DummyResponse(200, {"access_token": "token123"})
    )

    # First response is for token
    paypal.main(
        operation="get_order",
        order_id="ORDER123",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        dry_run=False,
        client=fake_client,
    )

    # Token call happens, then get order
    assert len(fake_client.calls) == 2
    assert fake_client.calls[0][0] == "POST"  # Token request
    assert fake_client.calls[1][0] == "GET"   # Get order


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400, {"message": "Invalid amount"}, text="Bad Request"
        )
    )
    result = paypal.main(
        operation="create_order",
        amount="50.00",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        dry_run=False,
        client=fake_client,
    )

    # Token endpoint returns error
    assert "error" in result["output"]


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))
    result = paypal.main(
        operation="create_order",
        amount="50.00",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Failed to obtain PayPal access token"


def test_sandbox_url_used_by_default():
    result = paypal.main(
        operation="create_order",
        amount="50.00",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        sandbox=True,
    )

    preview = result["output"]["preview"]
    assert "sandbox" in preview["url"]


def test_production_url_when_sandbox_false():
    result = paypal.main(
        operation="create_order",
        amount="50.00",
        PAYPAL_CLIENT_ID="client_id",
        PAYPAL_CLIENT_SECRET="secret",
        sandbox=False,
    )

    preview = result["output"]["preview"]
    assert "sandbox" not in preview["url"]
    assert "api-m.paypal.com" in preview["url"]
