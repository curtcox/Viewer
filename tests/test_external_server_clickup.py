import requests
from typing import Any

from reference_templates.servers.definitions import clickup


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
    result = clickup.main(dry_run=False)

    assert result["output"]["error"] == "Missing CLICKUP_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = clickup.main(operation="unknown", CLICKUP_API_KEY="key")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_team = clickup.main(operation="list_spaces", CLICKUP_API_KEY="key")
    missing_space = clickup.main(operation="get_space", CLICKUP_API_KEY="key")
    missing_list = clickup.main(operation="list_tasks", CLICKUP_API_KEY="key")
    missing_task = clickup.main(operation="get_task", CLICKUP_API_KEY="key")
    missing_name = clickup.main(operation="create_task", list_id="123", CLICKUP_API_KEY="key")

    assert missing_team["output"]["error"]["message"] == "Missing required team_id"
    assert missing_space["output"]["error"]["message"] == "Missing required space_id"
    assert missing_list["output"]["error"]["message"] == "Missing required list_id"
    assert missing_task["output"]["error"]["message"] == "Missing required task_id"
    assert missing_name["output"]["error"]["message"] == "Missing required name"


def test_dry_run_preview_for_list_spaces():
    result = clickup.main(operation="list_spaces", team_id="123", CLICKUP_API_KEY="key")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_spaces"
    assert "team/123" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_task():
    result = clickup.main(
        operation="create_task",
        list_id="456",
        name="New task",
        description="Details",
        CLICKUP_API_KEY="key",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_task"
    assert preview["method"] == "POST"
    assert preview["payload"]["name"] == "New task"
    assert preview["payload"]["description"] == "Details"


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = clickup.main(
        operation="list_spaces",
        team_id="123",
        CLICKUP_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "ClickUp request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = clickup.main(
        operation="list_spaces",
        team_id="123",
        CLICKUP_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"err": "Bad request"})
    client = FakeClient(response=response)

    result = clickup.main(
        operation="list_spaces",
        team_id="123",
        CLICKUP_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = {"spaces": [{"id": "1", "name": "Space 1"}]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = clickup.main(
        operation="list_spaces",
        team_id="123",
        CLICKUP_API_KEY="key",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
