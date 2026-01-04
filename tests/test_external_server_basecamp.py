import requests
from typing import Any

from reference.templates.servers.definitions import basecamp


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


def test_missing_access_token_returns_auth_error():
    result = basecamp.main(dry_run=False, account_id="123")

    assert result["output"]["error"] == "Missing BASECAMP_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_missing_account_id_returns_error():
    result = basecamp.main(dry_run=False, BASECAMP_ACCESS_TOKEN="token")

    assert result["output"]["error"] == "Missing account_id"
    assert result["output"]["status_code"] == 400


def test_invalid_operation_returns_validation_error():
    result = basecamp.main(operation="unknown", account_id="123", BASECAMP_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_project = basecamp.main(operation="get_project", account_id="123", BASECAMP_ACCESS_TOKEN="token")
    missing_todolist = basecamp.main(operation="list_todos", account_id="123", BASECAMP_ACCESS_TOKEN="token")
    missing_todo = basecamp.main(operation="get_todo", account_id="123", BASECAMP_ACCESS_TOKEN="token")
    missing_content = basecamp.main(operation="create_todo", todolist_id="123", account_id="123", BASECAMP_ACCESS_TOKEN="token")

    assert missing_project["output"]["error"]["message"] == "Missing required project_id"
    assert missing_todolist["output"]["error"]["message"] == "Missing required todolist_id"
    assert missing_todo["output"]["error"]["message"] == "Missing required todo_id"
    assert missing_content["output"]["error"]["message"] == "Missing required content"


def test_dry_run_preview_for_list_projects():
    result = basecamp.main(operation="list_projects", account_id="123", BASECAMP_ACCESS_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_projects"
    assert "basecampapi.com/123" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_todo():
    result = basecamp.main(
        operation="create_todo",
        account_id="123",
        project_id="456",
        todolist_id="789",
        content="New todo",
        description="Details",
        BASECAMP_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_todo"
    assert preview["method"] == "POST"
    assert preview["payload"]["content"] == "New todo"
    assert preview["payload"]["description"] == "Details"


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = basecamp.main(
        operation="list_projects",
        account_id="123",
        BASECAMP_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Basecamp request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = basecamp.main(
        operation="list_projects",
        account_id="123",
        BASECAMP_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"error": "Bad request"})
    client = FakeClient(response=response)

    result = basecamp.main(
        operation="list_projects",
        account_id="123",
        BASECAMP_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = [{"id": "1", "name": "Project 1"}]
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = basecamp.main(
        operation="list_projects",
        account_id="123",
        BASECAMP_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
