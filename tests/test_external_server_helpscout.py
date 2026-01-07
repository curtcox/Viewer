import requests

from reference.templates.servers.definitions import helpscout


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


def test_missing_api_key_returns_auth_error():
    result = helpscout.main(HELPSCOUT_API_KEY="", dry_run=False)
    assert result["output"]["error"] == "Missing HELPSCOUT_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = helpscout.main(HELPSCOUT_API_KEY="key", operation="unknown")
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_conversation_requires_conversation_id():
    result = helpscout.main(HELPSCOUT_API_KEY="key", operation="get_conversation")
    assert result["output"]["error"]["message"] == "Missing required conversation_id"


def test_create_conversation_requires_fields():
    missing_mailbox = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        subject="Test",
        customer_email="user@example.com",
        text="Message",
    )
    missing_subject = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        mailbox_id="123",
        customer_email="user@example.com",
        text="Message",
    )
    missing_email = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        mailbox_id="123",
        subject="Test",
        text="Message",
    )
    missing_text = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        mailbox_id="123",
        subject="Test",
        customer_email="user@example.com",
    )

    assert missing_mailbox["output"]["error"]["message"] == "Missing required mailbox_id"
    assert missing_subject["output"]["error"]["message"] == "Missing required subject"
    assert missing_email["output"]["error"]["message"] == "Missing required customer_email"
    assert missing_text["output"]["error"]["message"] == "Missing required text"


def test_get_customer_requires_customer_id():
    result = helpscout.main(HELPSCOUT_API_KEY="key", operation="get_customer")
    assert result["output"]["error"]["message"] == "Missing required customer_id"


def test_create_customer_requires_fields():
    missing_first = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_customer",
        last_name="Doe",
        email="john@example.com",
    )
    missing_last = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_customer",
        first_name="John",
        email="john@example.com",
    )
    missing_email = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_customer",
        first_name="John",
        last_name="Doe",
    )

    assert missing_first["output"]["error"]["message"] == "Missing required first_name"
    assert missing_last["output"]["error"]["message"] == "Missing required last_name"
    assert missing_email["output"]["error"]["message"] == "Missing required email"


def test_dry_run_returns_preview_for_list_conversations():
    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="list_conversations",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "list_conversations"
    assert preview["url"] == "https://api.helpscout.net/v2/conversations"
    assert preview["method"] == "GET"


def test_dry_run_returns_preview_for_create_conversation():
    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        mailbox_id="123",
        subject="Need help",
        customer_email="user@example.com",
        text="I have a question",
        dry_run=True,
    )

    assert "preview" in result["output"]
    preview = result["output"]["preview"]
    assert preview["operation"] == "create_conversation"
    assert preview["method"] == "POST"
    assert "payload" in preview


def test_list_conversations_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"_embedded": {"conversations": [{"id": 1}]}},
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert "_embedded" in result["output"]
    assert len(fake_client.calls) == 1
    method, url, _kwargs = fake_client.calls[0]
    assert method == "GET"
    assert url == "https://api.helpscout.net/v2/conversations"


def test_get_conversation_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": 123, "subject": "Test"},
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="get_conversation",
        conversation_id="123",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == 123
    assert len(fake_client.calls) == 1


def test_create_conversation_success():
    fake_response = DummyResponse(
        status_code=201,
        json_data={"id": 456, "subject": "New"},
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_conversation",
        mailbox_id="999",
        subject="New",
        customer_email="user@example.com",
        text="Help me",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == 456
    assert len(fake_client.calls) == 1
    method, _url, _kwargs = fake_client.calls[0]
    assert method == "POST"


def test_create_customer_success():
    fake_response = DummyResponse(
        status_code=201,
        json_data={"id": 789, "email": "john@example.com"},
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="create_customer",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["email"] == "john@example.com"
    assert len(fake_client.calls) == 1


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Network error"))

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Help Scout request failed"
    assert "Network error" in result["output"]["details"]


def test_invalid_json_response():
    fake_response = DummyResponse(
        status_code=200,
        json_data=ValueError("Invalid JSON"),
        text="<html>Not JSON</html>",
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_response():
    fake_response = DummyResponse(
        status_code=401,
        json_data={"message": "Unauthorized"},
    )
    fake_client = FakeClient(response=fake_response)

    result = helpscout.main(
        HELPSCOUT_API_KEY="key",
        operation="list_conversations",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["error"] == "Unauthorized"
    assert result["output"]["status_code"] == 401
