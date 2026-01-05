import requests
from typing import Any

from reference.templates.servers.definitions import monday


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

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_missing_api_key_returns_auth_error():
    result = monday.main(dry_run=False)

    assert result["output"]["error"] == "Missing MONDAY_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = monday.main(operation="unknown", MONDAY_API_KEY="key")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_board = monday.main(operation="get_board", MONDAY_API_KEY="key")
    missing_board_items = monday.main(operation="list_items", MONDAY_API_KEY="key")
    missing_item = monday.main(operation="get_item", MONDAY_API_KEY="key")
    missing_board_create = monday.main(operation="create_item", item_name="Test", MONDAY_API_KEY="key")
    missing_name = monday.main(operation="create_item", board_id="123", MONDAY_API_KEY="key")

    assert missing_board["output"]["error"]["message"] == "Missing required board_id"
    assert missing_board_items["output"]["error"]["message"] == "Missing required board_id"
    assert missing_item["output"]["error"]["message"] == "Missing required item_id"
    assert missing_board_create["output"]["error"]["message"] == "Missing required board_id for create_item"
    assert missing_name["output"]["error"]["message"] == "Missing required item_name"


def test_dry_run_preview_for_list_boards():
    result = monday.main(operation="list_boards", MONDAY_API_KEY="key")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_boards"
    assert "query" in preview["payload"]
    assert preview["method"] == "POST"


def test_dry_run_preview_for_create_item():
    result = monday.main(
        operation="create_item",
        board_id="123",
        item_name="New item",
        MONDAY_API_KEY="key",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_item"
    assert preview["method"] == "POST"
    assert "create_item" in preview["payload"]["query"]


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = monday.main(
        operation="list_boards",
        MONDAY_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Monday.com request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = monday.main(
        operation="list_boards",
        MONDAY_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"error_message": "Bad request"})
    client = FakeClient(response=response)

    result = monday.main(
        operation="list_boards",
        MONDAY_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = {"data": {"boards": [{"id": "1", "name": "Board 1"}]}}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = monday.main(
        operation="list_boards",
        MONDAY_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload["data"]}
    assert client.calls[0][0] == "POST"
