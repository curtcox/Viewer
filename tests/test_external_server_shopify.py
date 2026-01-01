from __future__ import annotations

import requests

from reference_templates.servers.definitions import shopify


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


def test_requires_access_token_for_api_operations():
    result = shopify.main(SHOPIFY_STORE_URL="mystore.myshopify.com")

    assert result["output"]["error"] == "Missing SHOPIFY_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_requires_store_url_for_api_operations():
    result = shopify.main(SHOPIFY_ACCESS_TOKEN="token")

    assert result["output"]["error"] == "Missing SHOPIFY_STORE_URL"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = shopify.main(
        operation="unknown",
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_product_requires_title():
    result = shopify.main(
        operation="create_product",
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
    )

    assert result["output"]["error"]["message"] == "Missing required title"


def test_get_product_requires_id():
    result = shopify.main(
        operation="get_product",
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
    )

    assert result["output"]["error"]["message"] == "Missing required product_id"


def test_dry_run_preview_for_list_products():
    result = shopify.main(
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        limit=5,
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_products"
    assert preview["params"] == {"limit": 5}
    assert "mystore.myshopify.com" in preview["url"]


def test_dry_run_preview_for_create_product():
    result = shopify.main(
        operation="create_product",
        title="Test Product",
        price="29.99",
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_product"
    assert preview["payload"]["product"]["title"] == "Test Product"


def test_list_products_success():
    fake_client = FakeClient(
        response=DummyResponse(200, {"products": [{"id": 1, "title": "Product"}]})
    )
    result = shopify.main(
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["products"][0]["title"] == "Product"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_create_product_success():
    fake_client = FakeClient(
        response=DummyResponse(201, {"product": {"id": 1, "title": "New Product"}})
    )
    result = shopify.main(
        operation="create_product",
        title="New Product",
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["product"]["title"] == "New Product"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "POST"


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400, {"errors": "Product title is required"}, text="Bad Request"
        )
    )
    result = shopify.main(
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))
    result = shopify.main(
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Shopify request failed"


def test_invalid_json_response():
    fake_client = FakeClient(response=DummyResponse(200, ValueError("Invalid JSON")))
    result = shopify.main(
        SHOPIFY_ACCESS_TOKEN="token",
        SHOPIFY_STORE_URL="mystore.myshopify.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"


def test_process_webhook_requires_secret():
    result = shopify.main(
        operation="process_webhook",
        webhook_payload='{"event": "test"}',
        hmac_header="abc123",
    )

    assert result["output"]["error"] == "Missing SHOPIFY_WEBHOOK_SECRET"


def test_process_webhook_dry_run():
    result = shopify.main(
        operation="process_webhook",
        webhook_payload='{"event": "test"}',
        hmac_header="abc123",
        SHOPIFY_WEBHOOK_SECRET="secret",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "process_webhook"
    assert preview["message"] == "Dry run - webhook not validated"
