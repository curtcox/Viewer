from __future__ import annotations

import requests

from reference_templates.servers.definitions import ebay


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


def test_requires_access_token():
    result = ebay.main()

    assert result["output"]["error"] == "Missing EBAY_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = ebay.main(operation="unknown", EBAY_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_search_items_requires_query_or_category():
    result = ebay.main(operation="search_items", EBAY_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Missing required query or category_id"


def test_get_item_requires_id():
    result = ebay.main(operation="get_item", EBAY_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Missing required item_id"


def test_dry_run_preview_for_search_items():
    result = ebay.main(
        operation="search_items", query="laptop", limit=5, EBAY_ACCESS_TOKEN="token"
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "search_items"
    assert preview["params"]["q"] == "laptop"
    assert preview["params"]["limit"] == 5


def test_dry_run_preview_for_get_item():
    result = ebay.main(
        operation="get_item", item_id="12345", EBAY_ACCESS_TOKEN="token"
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "get_item"
    assert "12345" in preview["url"]


def test_search_items_success():
    fake_client = FakeClient(
        response=DummyResponse(
            200, {"itemSummaries": [{"itemId": "123", "title": "Laptop"}]}
        )
    )
    result = ebay.main(
        operation="search_items",
        query="laptop",
        EBAY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["itemSummaries"][0]["title"] == "Laptop"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_get_item_success():
    fake_client = FakeClient(
        response=DummyResponse(200, {"itemId": "123", "title": "Laptop"})
    )
    result = ebay.main(
        operation="get_item",
        item_id="123",
        EBAY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["title"] == "Laptop"
    assert len(fake_client.calls) == 1


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400, {"errors": [{"message": "Invalid query"}]}, text="Bad Request"
        )
    )
    result = ebay.main(
        operation="search_items",
        query="laptop",
        EBAY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))
    result = ebay.main(
        operation="search_items",
        query="laptop",
        EBAY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "eBay request failed"


def test_invalid_json_response():
    fake_client = FakeClient(response=DummyResponse(200, ValueError("Invalid JSON")))
    result = ebay.main(
        operation="search_items",
        query="laptop",
        EBAY_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
