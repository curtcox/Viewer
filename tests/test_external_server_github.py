import pytest
import requests
from typing import Any

from reference_templates.servers.definitions import github


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


def test_missing_required_fields():
    missing_owner = github.main(owner="", repo="repo")
    missing_repo = github.main(owner="octocat", repo="")

    assert missing_owner["output"]["error"]["message"] == "Missing required owner"
    assert missing_repo["output"]["error"]["message"] == "Missing required repo"


def test_missing_token_returns_auth_error():
    result = github.main(owner="octocat", repo="hello-world", GITHUB_TOKEN="", dry_run=False)

    assert result["output"]["error"] == "Missing GITHUB_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = github.main(owner="octocat", repo="hello-world", operation="unknown")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_issue_requires_title():
    result = github.main(
        owner="octocat",
        repo="hello-world",
        operation="create_issue",
        GITHUB_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required title"


def test_get_issue_requires_issue_number():
    result = github.main(
        owner="octocat",
        repo="hello-world",
        operation="get_issue",
        GITHUB_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required issue_number"


def test_dry_run_returns_preview_for_list():
    result = github.main(owner="octocat", repo="hello-world", GITHUB_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_issues"
    assert "params" in preview


def test_dry_run_returns_preview_for_create():
    result = github.main(
        owner="octocat",
        repo="hello-world",
        operation="create_issue",
        title="Bug report",
        body="Found an issue",
        GITHUB_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["payload"] == {"title": "Bug report", "body": "Found an issue"}


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = github.main(
        owner="octocat",
        repo="hello-world",
        GITHUB_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "GitHub request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = github.main(
        owner="octocat",
        repo="hello-world",
        GITHUB_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_propagates_status_and_message():
    response = DummyResponse(status_code=404, json_data={"message": "Not Found"})
    client = FakeClient(response=response)

    result = github.main(
        owner="octocat",
        repo="hello-world",
        GITHUB_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Not Found"
    assert result["output"]["status_code"] == 404
    assert result["output"]["response"] == {"message": "Not Found"}


def test_success_returns_payload():
    payload = [{"title": "Issue 1"}]
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = github.main(
        owner="octocat",
        repo="hello-world",
        GITHUB_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
