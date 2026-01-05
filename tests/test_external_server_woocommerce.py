from __future__ import annotations

import requests

from reference.templates.servers.definitions import woocommerce


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


def test_requires_consumer_key():
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
    )

    assert result["output"]["error"] == "Missing WOOCOMMERCE_CONSUMER_KEY"
    assert result["output"]["status_code"] == 401


def test_requires_consumer_secret():
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key", WOOCOMMERCE_STORE_URL="https://mystore.com"
    )

    assert result["output"]["error"] == "Missing WOOCOMMERCE_CONSUMER_SECRET"
    assert result["output"]["status_code"] == 401


def test_requires_store_url():
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key", WOOCOMMERCE_CONSUMER_SECRET="secret"
    )

    assert result["output"]["error"] == "Missing WOOCOMMERCE_STORE_URL"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = woocommerce.main(
        operation="unknown",
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_product_requires_name():
    result = woocommerce.main(
        operation="create_product",
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
    )

    assert result["output"]["error"]["message"] == "Missing required name"


def test_get_product_requires_id():
    result = woocommerce.main(
        operation="get_product",
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
    )

    assert result["output"]["error"]["message"] == "Missing required product_id"


def test_dry_run_preview_for_list_products():
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        limit=5,
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_products"
    assert preview["params"] == {"per_page": 5}
    assert "mystore.com" in preview["url"]


def test_dry_run_preview_for_create_product():
    result = woocommerce.main(
        operation="create_product",
        name="Test Product",
        regular_price="29.99",
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_product"
    assert preview["payload"]["name"] == "Test Product"


def test_list_products_success():
    fake_client = FakeClient(
        response=DummyResponse(200, [{"id": 1, "name": "Product"}])
    )
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"][0]["name"] == "Product"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_create_product_success():
    fake_client = FakeClient(
        response=DummyResponse(201, {"id": 1, "name": "New Product"})
    )
    result = woocommerce.main(
        operation="create_product",
        name="New Product",
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["name"] == "New Product"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "POST"


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400, {"message": "Product name is required"}, text="Bad Request"
        )
    )
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "WooCommerce request failed"


def test_invalid_json_response():
    fake_client = FakeClient(response=DummyResponse(200, ValueError("Invalid JSON")))
    result = woocommerce.main(
        WOOCOMMERCE_CONSUMER_KEY="key",
        WOOCOMMERCE_CONSUMER_SECRET="secret",
        WOOCOMMERCE_STORE_URL="https://mystore.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
