import requests
from typing import Any

from reference.templates.servers.definitions import whatsapp


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


def test_missing_access_token_returns_auth_error():
    result = whatsapp.main(dry_run=False, WHATSAPP_PHONE_NUMBER_ID="123456")

    assert result["output"]["error"] == "Missing WHATSAPP_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_missing_phone_number_id_returns_auth_error():
    result = whatsapp.main(dry_run=False, WHATSAPP_ACCESS_TOKEN="token")

    assert result["output"]["error"] == "Missing WHATSAPP_PHONE_NUMBER_ID"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = whatsapp.main(
        operation="unknown",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_to = whatsapp.main(
        operation="send_message",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )
    missing_text = whatsapp.main(
        operation="send_message",
        to="+15551234567",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )
    missing_template = whatsapp.main(
        operation="send_template",
        to="+15551234567",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )

    assert missing_to["output"]["error"]["message"] == "Missing required to"
    assert missing_text["output"]["error"]["message"] == "Missing required text_body"
    assert missing_template["output"]["error"]["message"] == "Missing required template_name"


def test_dry_run_preview_for_send_message():
    result = whatsapp.main(
        operation="send_message",
        to="+15551234567",
        text_body="Hello WhatsApp!",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_message"
    assert preview["method"] == "POST"
    assert "/messages" in preview["url"]
    assert preview["payload"]["to"] == "+15551234567"
    assert preview["payload"]["text"]["body"] == "Hello WhatsApp!"


def test_dry_run_preview_for_send_template():
    result = whatsapp.main(
        operation="send_template",
        to="+15551234567",
        template_name="hello_world",
        template_language="en_US",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_template"
    assert preview["method"] == "POST"
    assert preview["payload"]["template"]["name"] == "hello_world"
    assert preview["payload"]["template"]["language"]["code"] == "en_US"


def test_dry_run_preview_for_mark_as_read():
    result = whatsapp.main(
        operation="mark_as_read",
        message_id="wamid.123",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "mark_as_read"
    assert preview["method"] == "POST"
    assert preview["payload"]["status"] == "read"
    assert preview["payload"]["message_id"] == "wamid.123"


def test_send_message_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"messaging_product": "whatsapp", "messages": [{"id": "wamid.123"}]},
    )
    fake_client = FakeClient(response=fake_response)

    result = whatsapp.main(
        operation="send_message",
        to="+15551234567",
        text_body="Hello WhatsApp!",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["messaging_product"] == "whatsapp"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert "/messages" in url
    assert "Bearer token" in kwargs["headers"]["Authorization"]
    assert kwargs["json"]["text"]["body"] == "Hello WhatsApp!"


def test_send_template_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"messaging_product": "whatsapp", "messages": [{"id": "wamid.456"}]},
    )
    fake_client = FakeClient(response=fake_response)

    result = whatsapp.main(
        operation="send_template",
        to="+15551234567",
        template_name="hello_world",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["messaging_product"] == "whatsapp"
    assert len(fake_client.calls) == 1
    method, _url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert kwargs["json"]["template"]["name"] == "hello_world"


def test_api_error_handling():
    fake_response = DummyResponse(
        status_code=400,
        json_data={"error": {"message": "Invalid phone number"}},
    )
    fake_client = FakeClient(response=fake_response)

    result = whatsapp.main(
        operation="send_message",
        to="invalid",
        text_body="Test",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    exc = requests.exceptions.RequestException("Network error")
    exc.response = None
    fake_client = FakeClient(exc=exc)

    result = whatsapp.main(
        operation="send_message",
        to="+15551234567",
        text_body="Test",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
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

    result = whatsapp.main(
        operation="send_message",
        to="+15551234567",
        text_body="Test",
        WHATSAPP_ACCESS_TOKEN="token",
        WHATSAPP_PHONE_NUMBER_ID="123456",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
