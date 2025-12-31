import requests
from typing import Any

from reference_templates.servers.definitions import jira


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
    result = jira.main(dry_run=False, JIRA_EMAIL="test@test.com", JIRA_DOMAIN="test.atlassian.net")

    assert result["output"]["error"] == "Missing JIRA_API_TOKEN"
    assert result["output"]["status_code"] == 401


def test_missing_email_returns_auth_error():
    result = jira.main(dry_run=False, JIRA_API_TOKEN="token", JIRA_DOMAIN="test.atlassian.net")

    assert result["output"]["error"] == "Missing JIRA_EMAIL"
    assert result["output"]["status_code"] == 401


def test_missing_domain_returns_auth_error():
    result = jira.main(dry_run=False, JIRA_API_TOKEN="token", JIRA_EMAIL="test@test.com")

    assert result["output"]["error"] == "Missing JIRA_DOMAIN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = jira.main(
        operation="unknown",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_project = jira.main(
        operation="get_project",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )
    missing_jql = jira.main(
        operation="list_issues",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )
    missing_issue = jira.main(
        operation="get_issue",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )
    missing_summary = jira.main(
        operation="create_issue",
        project_key="TEST",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )

    assert missing_project["output"]["error"]["message"] == "Missing required project_key"
    assert missing_jql["output"]["error"]["message"] == "Missing required jql"
    assert missing_issue["output"]["error"]["message"] == "Missing required issue_key"
    assert missing_summary["output"]["error"]["message"] == "Missing required summary"


def test_dry_run_preview_for_list_projects():
    result = jira.main(
        operation="list_projects",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_projects"
    assert "test.atlassian.net" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_issue():
    result = jira.main(
        operation="create_issue",
        project_key="TEST",
        summary="New issue",
        description="Details",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_issue"
    assert preview["method"] == "POST"
    assert preview["payload"]["fields"]["project"]["key"] == "TEST"
    assert preview["payload"]["fields"]["summary"] == "New issue"


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = jira.main(
        operation="list_projects",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Jira request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = jira.main(
        operation="list_projects",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"errorMessages": ["Bad request"]})
    client = FakeClient(response=response)

    result = jira.main(
        operation="list_projects",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = [{"key": "TEST", "name": "Test Project"}]
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = jira.main(
        operation="list_projects",
        JIRA_API_TOKEN="token",
        JIRA_EMAIL="test@test.com",
        JIRA_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
