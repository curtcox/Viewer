from __future__ import annotations

import requests

from reference.templates.servers.definitions import etsy


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

    def put(self, url: str, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_access_token():
    result = etsy.main()

    assert result["output"]["error"] == "Missing ETSY_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = etsy.main(operation="unknown", ETSY_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_shop_requires_shop_id():
    result = etsy.main(operation="get_shop", ETSY_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Missing required shop_id"


def test_create_listing_requires_shop_id():
    result = etsy.main(
        operation="create_listing", title="Test", price="10.00", ETSY_ACCESS_TOKEN="token"
    )

    assert result["output"]["error"]["message"] == "Missing required shop_id"


def test_create_listing_requires_title():
    result = etsy.main(
        operation="create_listing", shop_id="123", price="10.00", ETSY_ACCESS_TOKEN="token"
    )

    assert result["output"]["error"]["message"] == "Missing required title"


def test_dry_run_preview_for_list_shops():
    result = etsy.main(operation="list_shops", limit=5, ETSY_ACCESS_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_shops"
    assert preview["params"] == {"limit": 5}


def test_dry_run_preview_for_create_listing():
    result = etsy.main(
        operation="create_listing",
        shop_id="123",
        title="Handmade Item",
        price="25.00",
        ETSY_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_listing"
    assert preview["payload"]["title"] == "Handmade Item"


def test_list_shops_success():
    fake_client = FakeClient(
        response=DummyResponse(200, {"results": [{"shop_id": 123, "shop_name": "MyShop"}]})
    )
    result = etsy.main(
        operation="list_shops",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["results"][0]["shop_name"] == "MyShop"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_create_listing_success():
    fake_client = FakeClient(
        response=DummyResponse(201, {"listing_id": 456, "title": "New Listing"})
    )
    result = etsy.main(
        operation="create_listing",
        shop_id="123",
        title="New Listing",
        price="15.00",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["title"] == "New Listing"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "POST"


def test_update_listing_success():
    fake_client = FakeClient(
        response=DummyResponse(200, {"listing_id": 456, "title": "Updated Listing"})
    )
    result = etsy.main(
        operation="update_listing",
        listing_id="456",
        title="Updated Listing",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["title"] == "Updated Listing"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "PUT"


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(400, {"error": "Invalid shop_id"}, text="Bad Request")
    )
    result = etsy.main(
        operation="get_shop",
        shop_id="123",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))
    result = etsy.main(
        operation="list_shops",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Etsy request failed"


def test_invalid_json_response():
    fake_client = FakeClient(response=DummyResponse(200, ValueError("Invalid JSON")))
    result = etsy.main(
        operation="list_shops",
        ETSY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
