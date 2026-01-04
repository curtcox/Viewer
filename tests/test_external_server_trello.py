import requests
from typing import Any

from reference.templates.servers.definitions import trello


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


def test_missing_api_key_returns_auth_error():
    result = trello.main(dry_run=False, TRELLO_TOKEN="token")

    assert result["output"]["error"] == "Missing TRELLO_API_KEY"
    assert result["output"]["status_code"] == 401


def test_missing_token_returns_auth_error():
    result = trello.main(dry_run=False, TRELLO_API_KEY="key")

    assert result["output"]["error"] == "Missing TRELLO_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = trello.main(operation="unknown", TRELLO_API_KEY="key", TRELLO_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_board = trello.main(operation="get_board", TRELLO_API_KEY="key", TRELLO_TOKEN="token")
    missing_list = trello.main(operation="list_cards", TRELLO_API_KEY="key", TRELLO_TOKEN="token")
    missing_card = trello.main(operation="get_card", TRELLO_API_KEY="key", TRELLO_TOKEN="token")
    missing_name = trello.main(operation="create_card", list_id="123", TRELLO_API_KEY="key", TRELLO_TOKEN="token")

    assert missing_board["output"]["error"]["message"] == "Missing required board_id"
    assert missing_list["output"]["error"]["message"] == "Missing required list_id"
    assert missing_card["output"]["error"]["message"] == "Missing required card_id"
    assert missing_name["output"]["error"]["message"] == "Missing required name"


def test_dry_run_preview_for_list_boards():
    result = trello.main(operation="list_boards", TRELLO_API_KEY="key", TRELLO_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_boards"
    assert preview["params"]["key"] == "key"
    assert preview["params"]["token"] == "token"
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_card():
    result = trello.main(
        operation="create_card",
        list_id="456",
        name="New card",
        description="Details",
        TRELLO_API_KEY="key",
        TRELLO_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_card"
    assert preview["method"] == "POST"
    assert preview["params"]["idList"] == "456"
    assert preview["params"]["name"] == "New card"
    assert preview["params"]["desc"] == "Details"


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = trello.main(
        operation="list_boards",
        TRELLO_API_KEY="key",
        TRELLO_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Trello request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = trello.main(
        operation="list_boards",
        TRELLO_API_KEY="key",
        TRELLO_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"message": "Bad request"})
    client = FakeClient(response=response)

    result = trello.main(
        operation="list_boards",
        TRELLO_API_KEY="key",
        TRELLO_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = [{"id": "1", "name": "Board 1"}]
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = trello.main(
        operation="list_boards",
        TRELLO_API_KEY="key",
        TRELLO_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
