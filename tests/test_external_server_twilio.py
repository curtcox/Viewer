import requests
from typing import Any

from reference.templates.servers.definitions import twilio


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

    def request(self, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_missing_account_sid_returns_auth_error():
    result = twilio.main(dry_run=False, TWILIO_AUTH_TOKEN="token")

    assert result["output"]["error"] == "Missing TWILIO_ACCOUNT_SID"
    assert result["output"]["status_code"] == 401


def test_missing_auth_token_returns_auth_error():
    result = twilio.main(dry_run=False, TWILIO_ACCOUNT_SID="ACxxx")

    assert result["output"]["error"] == "Missing TWILIO_AUTH_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = twilio.main(
        operation="unknown",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_to = twilio.main(
        operation="send_sms",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )
    missing_body = twilio.main(
        operation="send_sms",
        to="+15551234567",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )
    missing_from = twilio.main(
        operation="send_sms",
        to="+15551234567",
        body="Hello",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )

    assert missing_to["output"]["error"]["message"] == "Missing required to"
    assert missing_body["output"]["error"]["message"] == "Missing required body"
    assert missing_from["output"]["error"]["message"] == "Missing required from_"


def test_dry_run_preview_for_send_sms():
    result = twilio.main(
        operation="send_sms",
        to="+15551234567",
        from_="+15559876543",
        body="Hello from Twilio!",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_sms"
    assert preview["method"] == "POST"
    assert "Messages.json" in preview["url"]
    assert preview["payload"]["To"] == "+15551234567"
    assert preview["payload"]["Body"] == "Hello from Twilio!"


def test_dry_run_preview_for_send_whatsapp():
    result = twilio.main(
        operation="send_whatsapp",
        to="+15551234567",
        from_="+15559876543",
        body="Hello via WhatsApp!",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_whatsapp"
    assert preview["method"] == "POST"
    assert "whatsapp:" in preview["payload"]["To"]
    assert preview["payload"]["Body"] == "Hello via WhatsApp!"


def test_dry_run_preview_for_make_call():
    result = twilio.main(
        operation="make_call",
        to="+15551234567",
        from_="+15559876543",
        url="http://demo.twilio.com/docs/voice.xml",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "make_call"
    assert preview["method"] == "POST"
    assert "Calls.json" in preview["url"]
    assert preview["payload"]["Url"] == "http://demo.twilio.com/docs/voice.xml"


def test_send_sms_success():
    fake_response = DummyResponse(
        status_code=201,
        json_data={"sid": "SM123", "status": "queued", "body": "Hello from Twilio!"},
    )
    fake_client = FakeClient(response=fake_response)

    result = twilio.main(
        operation="send_sms",
        to="+15551234567",
        from_="+15559876543",
        body="Hello from Twilio!",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["sid"] == "SM123"
    assert result["output"]["status"] == "queued"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert "Messages.json" in url
    assert kwargs["auth"] == ("ACxxx", "token")
    assert kwargs["data"]["Body"] == "Hello from Twilio!"


def test_list_messages_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"messages": [{"sid": "SM123", "body": "Test"}]},
    )
    fake_client = FakeClient(response=fake_response)

    result = twilio.main(
        operation="list_messages",
        limit=10,
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "messages" in result["output"]
    assert len(fake_client.calls) == 1
    method, _url, kwargs = fake_client.calls[0]
    assert method == "GET"
    assert kwargs["params"]["PageSize"] == 10


def test_api_error_handling():
    fake_response = DummyResponse(
        status_code=400,
        json_data={"message": "Invalid phone number"},
    )
    fake_client = FakeClient(response=fake_response)

    result = twilio.main(
        operation="send_sms",
        to="+15551234567",
        from_="+15559876543",
        body="Test",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    exc = requests.exceptions.RequestException("Network error")
    exc.response = None
    fake_client = FakeClient(exc=exc)

    result = twilio.main(
        operation="list_messages",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Network error" in result["output"]["error"]


def test_invalid_json_response():
    fake_response = DummyResponse(
        status_code=200,
        json_data=ValueError("Invalid JSON"),
        text="Not JSON",
    )
    fake_client = FakeClient(response=fake_response)

    result = twilio.main(
        operation="list_messages",
        TWILIO_ACCOUNT_SID="ACxxx",
        TWILIO_AUTH_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
