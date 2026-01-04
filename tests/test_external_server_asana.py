import requests
from typing import Any

from reference.templates.servers.definitions import asana


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


def test_missing_token_returns_auth_error():
    result = asana.main(dry_run=False)

    assert result["output"]["error"] == "Missing ASANA_PAT"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = asana.main(operation="unknown", ASANA_PAT="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_workspace = asana.main(operation="list_projects", ASANA_PAT="token")
    missing_project = asana.main(operation="list_tasks", ASANA_PAT="token")
    missing_task = asana.main(operation="get_task", ASANA_PAT="token")
    missing_name = asana.main(operation="create_task", ASANA_PAT="token")

    assert missing_workspace["output"]["error"]["message"] == "Missing required workspace_gid"
    assert missing_project["output"]["error"]["message"] == "Missing required project_gid"
    assert missing_task["output"]["error"]["message"] == "Missing required task_gid"
    assert missing_name["output"]["error"]["message"] == "Missing required name"


def test_dry_run_preview_for_list_projects():
    result = asana.main(operation="list_projects", workspace_gid="123", ASANA_PAT="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_projects"
    assert preview["params"] == {"workspace": "123", "limit": 20}
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_task():
    result = asana.main(
        operation="create_task",
        workspace_gid="123",
        project_gid="456",
        name="New task",
        notes="Details",
        assignee="me",
        ASANA_PAT="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_task"
    assert preview["method"] == "POST"
    assert preview["payload"] == {
        "name": "New task",
        "workspace": "123",
        "notes": "Details",
        "assignee": "me",
        "projects": ["456"],
    }


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = asana.main(
        operation="list_projects",
        workspace_gid="123",
        ASANA_PAT="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Asana request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = asana.main(
        operation="list_projects",
        workspace_gid="123",
        ASANA_PAT="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"errors": [{"message": "Bad request"}]})
    client = FakeClient(response=response)

    result = asana.main(
        operation="list_projects",
        workspace_gid="123",
        ASANA_PAT="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = {"data": [{"gid": "1", "name": "Project"}]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = asana.main(
        operation="list_projects",
        workspace_gid="123",
        ASANA_PAT="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload["data"]}
    assert client.calls[0][0] == "GET"
