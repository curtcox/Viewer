import requests
from typing import Any

from reference.templates.servers.definitions import todoist


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


def test_missing_api_token_returns_auth_error():
    result = todoist.main(dry_run=False)

    assert result["output"]["error"] == "Missing TODOIST_API_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = todoist.main(operation="unknown", TODOIST_API_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_project = todoist.main(operation="get_project", TODOIST_API_TOKEN="token")
    missing_project_tasks = todoist.main(operation="list_tasks", TODOIST_API_TOKEN="token")
    missing_task = todoist.main(operation="get_task", TODOIST_API_TOKEN="token")
    missing_content = todoist.main(operation="create_task", TODOIST_API_TOKEN="token")

    assert missing_project["output"]["error"]["message"] == "Missing required project_id"
    assert missing_project_tasks["output"]["error"]["message"] == "Missing required project_id"
    assert missing_task["output"]["error"]["message"] == "Missing required task_id"
    assert missing_content["output"]["error"]["message"] == "Missing required content"


def test_dry_run_preview_for_list_projects():
    result = todoist.main(operation="list_projects", TODOIST_API_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_projects"
    assert "todoist.com" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_task():
    result = todoist.main(
        operation="create_task",
        project_id="123",
        content="New task",
        description="Details",
        priority=3,
        TODOIST_API_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_task"
    assert preview["method"] == "POST"
    assert preview["payload"]["content"] == "New task"
    assert preview["payload"]["priority"] == 3


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = todoist.main(
        operation="list_projects",
        TODOIST_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Todoist request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = todoist.main(
        operation="list_projects",
        TODOIST_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"error": "Bad request"})
    client = FakeClient(response=response)

    result = todoist.main(
        operation="list_projects",
        TODOIST_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = [{"id": "1", "name": "Project 1"}]
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = todoist.main(
        operation="list_projects",
        TODOIST_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"


def test_close_task_with_no_content():
    response = DummyResponse(status_code=204, json_data=None)
    client = FakeClient(response=response)

    result = todoist.main(
        operation="close_task",
        task_id="123",
        TODOIST_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["success"] is True
    assert "completed" in result["output"]["message"].lower()
