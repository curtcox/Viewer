import pytest
import requests
from typing import Any

from reference_templates.servers.definitions import notion


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
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


def test_missing_token_returns_error():
    result = notion.main()

    assert result["output"]["error"] == "Missing NOTION_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_validation_error():
    result = notion.main(operation="unknown", NOTION_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_retrieve_requires_page_id():
    result = notion.main(operation="retrieve_page", NOTION_TOKEN="token")

    assert result["output"]["error"]["message"] == "Missing required page_id"


def test_create_requires_database_and_title():
    missing_db = notion.main(
        operation="create_page",
        NOTION_TOKEN="token",
        title="Title",
    )
    missing_title = notion.main(
        operation="create_page",
        NOTION_TOKEN="token",
        database_id="db",
    )

    assert missing_db["output"]["error"]["message"] == "Missing required database_id"
    assert missing_title["output"]["error"]["message"] == "Missing required title"


def test_dry_run_preview_search():
    result = notion.main(operation="search", query="example", NOTION_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["payload"] == {"query": "example"}


def test_dry_run_preview_retrieve():
    result = notion.main(operation="retrieve_page", page_id="abc", NOTION_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert "abc" in preview["url"]


def test_dry_run_preview_create():
    result = notion.main(
        operation="create_page",
        database_id="db",
        title="Task",
        NOTION_TOKEN="token",
        properties={"Status": {"select": {"name": "Todo"}}},
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["payload"]["properties"]["Name"]
    assert preview["payload"]["properties"]["Status"] == {"select": {"name": "Todo"}}


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = notion.main(NOTION_TOKEN="token", dry_run=False, client=client)

    assert result["output"]["error"] == "Notion request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = notion.main(NOTION_TOKEN="token", dry_run=False, client=client)

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_propagates_status_and_message():
    response = DummyResponse(status_code=400, json_data={"message": "Bad Request"})
    client = FakeClient(response=response)

    result = notion.main(NOTION_TOKEN="token", dry_run=False, client=client)

    assert result["output"]["error"] == "Bad Request"
    assert result["output"]["status_code"] == 400
    assert result["output"]["response"] == {"message": "Bad Request"}


def test_success_returns_payload():
    payload = {"results": ["page"]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = notion.main(NOTION_TOKEN="token", dry_run=False, client=client)

    assert result == {"output": payload}
    assert client.calls[0][0] == "POST"
