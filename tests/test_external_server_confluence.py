import requests
from typing import Any

from reference.templates.servers.definitions import confluence


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
    result = confluence.main(dry_run=False, CONFLUENCE_EMAIL="test@test.com", CONFLUENCE_DOMAIN="test.atlassian.net")

    assert result["output"]["error"] == "Missing CONFLUENCE_API_TOKEN"
    assert result["output"]["status_code"] == 401


def test_missing_email_returns_auth_error():
    result = confluence.main(dry_run=False, CONFLUENCE_API_TOKEN="token", CONFLUENCE_DOMAIN="test.atlassian.net")

    assert result["output"]["error"] == "Missing CONFLUENCE_EMAIL"
    assert result["output"]["status_code"] == 401


def test_missing_domain_returns_auth_error():
    result = confluence.main(dry_run=False, CONFLUENCE_API_TOKEN="token", CONFLUENCE_EMAIL="test@test.com")

    assert result["output"]["error"] == "Missing CONFLUENCE_DOMAIN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = confluence.main(
        operation="unknown",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_space = confluence.main(
        operation="get_space",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )
    missing_page = confluence.main(
        operation="get_page",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )
    missing_title = confluence.main(
        operation="create_page",
        space_key="TEST",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )

    assert missing_space["output"]["error"]["message"] == "Missing required space_key"
    assert missing_page["output"]["error"]["message"] == "Missing required page_id"
    assert missing_title["output"]["error"]["message"] == "Missing required title"


def test_dry_run_preview_for_list_spaces():
    result = confluence.main(
        operation="list_spaces",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_spaces"
    assert "test.atlassian.net" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_create_page():
    result = confluence.main(
        operation="create_page",
        space_key="TEST",
        title="New page",
        content="<p>Content</p>",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_page"
    assert preview["method"] == "POST"
    assert preview["payload"]["title"] == "New page"
    assert preview["payload"]["space"]["key"] == "TEST"


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = confluence.main(
        operation="list_spaces",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Confluence request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = confluence.main(
        operation="list_spaces",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"message": "Bad request"})
    client = FakeClient(response=response)

    result = confluence.main(
        operation="list_spaces",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = {"results": [{"key": "TEST", "name": "Test Space"}]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = confluence.main(
        operation="list_spaces",
        CONFLUENCE_API_TOKEN="token",
        CONFLUENCE_EMAIL="test@test.com",
        CONFLUENCE_DOMAIN="test.atlassian.net",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"
