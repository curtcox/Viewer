import requests

from reference_templates.servers.definitions import freshdesk


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data=None, text: str = ""):
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
        self.calls = []

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

    def put(self, url: str, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_missing_required_fields():
    missing_domain = freshdesk.main(domain="", FRESHDESK_API_KEY="key")
    assert missing_domain["output"]["error"]["message"] == "Missing required domain"


def test_missing_api_key_returns_auth_error():
    result = freshdesk.main(domain="example", FRESHDESK_API_KEY="", dry_run=False)
    assert result["output"]["error"] == "Missing FRESHDESK_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = freshdesk.main(domain="example", FRESHDESK_API_KEY="key", operation="unknown")
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_ticket_requires_ticket_id():
    result = freshdesk.main(domain="example", FRESHDESK_API_KEY="key", operation="get_ticket")
    assert result["output"]["error"]["message"] == "Missing required ticket_id"


def test_update_ticket_requires_ticket_id():
    result = freshdesk.main(domain="example", FRESHDESK_API_KEY="key", operation="update_ticket")
    assert result["output"]["error"]["message"] == "Missing required ticket_id"


def test_create_ticket_requires_subject_description_email():
    missing_subject = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="create_ticket",
        subject="",
        description="Issue description",
        email="user@example.com",
    )
    missing_description = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="create_ticket",
        subject="Issue",
        description="",
        email="user@example.com",
    )
    missing_email = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="create_ticket",
        subject="Issue",
        description="Issue description",
        email="",
    )

    assert missing_subject["output"]["error"]["message"] == "Missing required subject"
    assert missing_description["output"]["error"]["message"] == "Missing required description"
    assert missing_email["output"]["error"]["message"] == "Missing required email"


def test_dry_run_returns_preview_for_list():
    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="list_tickets",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "list_tickets"
    assert preview["url"] == "https://example.freshdesk.com/api/v2/tickets"
    assert preview["method"] == "GET"
    assert preview["auth"] == "basic"


def test_dry_run_returns_preview_for_create():
    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="create_ticket",
        subject="Help needed",
        description="Cannot access my account",
        email="user@example.com",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "create_ticket"
    assert preview["method"] == "POST"
    assert "payload" in preview
    assert preview["payload"]["subject"] == "Help needed"


def test_list_tickets_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data=[{"id": 1, "subject": "Test ticket"}],
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="list_tickets",
        dry_run=False,
        client=fake_client,
    )

    assert isinstance(result["output"], list)
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "GET"
    assert url == "https://example.freshdesk.com/api/v2/tickets"
    assert "Authorization" in kwargs["headers"]


def test_get_ticket_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": 123, "subject": "Test ticket"},
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="get_ticket",
        ticket_id=123,
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == 123
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "GET"
    assert url == "https://example.freshdesk.com/api/v2/tickets/123"


def test_create_ticket_success():
    fake_response = DummyResponse(
        status_code=201,
        json_data={"id": 456, "subject": "New ticket"},
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="create_ticket",
        subject="New ticket",
        description="Need help",
        email="user@example.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == 456
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert kwargs["json"]["subject"] == "New ticket"


def test_update_ticket_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": 789, "subject": "Updated ticket"},
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="update_ticket",
        ticket_id=789,
        subject="Updated ticket",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["subject"] == "Updated ticket"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "PUT"
    assert url == "https://example.freshdesk.com/api/v2/tickets/789"


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="list_tickets",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Freshdesk request failed"
    assert "Network error" in result["output"]["details"]


def test_invalid_json_response():
    fake_response = DummyResponse(
        status_code=200,
        json_data=ValueError("Invalid JSON"),
        text="<html>Not JSON</html>",
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="list_tickets",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_response():
    fake_response = DummyResponse(
        status_code=401,
        json_data={"description": "Authentication failed"},
    )
    fake_client = FakeClient(response=fake_response)

    result = freshdesk.main(
        domain="example",
        FRESHDESK_API_KEY="key",
        operation="list_tickets",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Authentication failed"
    assert result["output"]["status_code"] == 401
