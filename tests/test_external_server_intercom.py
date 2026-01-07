import requests

from reference.templates.servers.definitions import intercom


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


def test_missing_token_returns_auth_error():
    result = intercom.main(INTERCOM_ACCESS_TOKEN="", dry_run=False)

    assert result["output"]["error"] == "Missing INTERCOM_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = intercom.main(INTERCOM_ACCESS_TOKEN="token", operation="unknown")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_conversation_requires_conversation_id():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="get_conversation",
    )

    assert result["output"]["error"]["message"] == "Missing required conversation_id"


def test_reply_to_conversation_requires_conversation_id_message_and_admin_id():
    missing_conversation = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="reply_to_conversation",
        message="Reply text",
        admin_id="123",
    )
    missing_message = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="reply_to_conversation",
        conversation_id="456",
        admin_id="123",
    )
    missing_admin = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="reply_to_conversation",
        conversation_id="456",
        message="Reply text",
    )

    assert missing_conversation["output"]["error"]["message"] == "Missing required conversation_id"
    assert missing_message["output"]["error"]["message"] == "Missing required message"
    assert missing_admin["output"]["error"]["message"] == "Missing required admin_id"


def test_get_contact_requires_contact_id():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="get_contact",
    )

    assert result["output"]["error"]["message"] == "Missing required contact_id"


def test_create_contact_requires_email():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="create_contact",
        email="",
    )

    assert result["output"]["error"]["message"] == "Missing required email"


def test_dry_run_returns_preview_for_list_conversations():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="list_conversations",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "list_conversations"
    assert preview["url"] == "https://api.intercom.io/conversations"
    assert preview["method"] == "GET"
    assert preview["auth"] == "bearer"


def test_dry_run_returns_preview_for_reply():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="reply_to_conversation",
        conversation_id="789",
        admin_id="123",
        message="Thanks for contacting us",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "reply_to_conversation"
    assert preview["url"] == "https://api.intercom.io/conversations/789/reply"
    assert preview["method"] == "POST"
    assert "payload" in preview
    assert preview["payload"]["body"] == "Thanks for contacting us"


def test_dry_run_returns_preview_for_create_contact():
    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="create_contact",
        email="test@example.com",
        name="Test User",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "create_contact"
    assert preview["url"] == "https://api.intercom.io/contacts"
    assert preview["method"] == "POST"
    assert "payload" in preview


def test_list_conversations_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"conversations": [{"id": "1", "created_at": 1234567890}]},
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert "conversations" in result["output"]
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "GET"
    assert url == "https://api.intercom.io/conversations"
    assert kwargs["headers"]["Authorization"] == "Bearer token"


def test_get_conversation_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": "123", "created_at": 1234567890},
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="get_conversation",
        conversation_id="123",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "123"
    assert len(fake_client.calls) == 1
    method, url, _kwargs = fake_client.calls[0]
    assert method == "GET"
    assert url == "https://api.intercom.io/conversations/123"


def test_reply_to_conversation_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": "456", "message": "Reply sent"},
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="reply_to_conversation",
        conversation_id="456",
        admin_id="789",
        message="Thank you",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["message"] == "Reply sent"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert url == "https://api.intercom.io/conversations/456/reply"
    assert kwargs["json"]["body"] == "Thank you"
    assert kwargs["json"]["admin_id"] == "789"


def test_create_contact_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": "contact123", "email": "new@example.com"},
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="create_contact",
        email="new@example.com",
        name="New User",
        role="user",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["email"] == "new@example.com"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert url == "https://api.intercom.io/contacts"
    assert kwargs["json"]["email"] == "new@example.com"
    assert kwargs["json"]["name"] == "New User"


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Intercom request failed"
    assert "Network error" in result["output"]["details"]


def test_invalid_json_response():
    fake_response = DummyResponse(
        status_code=200,
        json_data=ValueError("Invalid JSON"),
        text="<html>Not JSON</html>",
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_response():
    fake_response = DummyResponse(
        status_code=401,
        json_data={"errors": [{"message": "Unauthorized"}]},
    )
    fake_client = FakeClient(response=fake_response)

    result = intercom.main(
        INTERCOM_ACCESS_TOKEN="token",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Unauthorized"
    assert result["output"]["status_code"] == 401
