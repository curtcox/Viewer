import requests
from typing import Any

from reference_templates.servers.definitions import telegram


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


def test_missing_token_returns_auth_error():
    result = telegram.main(dry_run=False)

    assert result["output"]["error"] == "Missing TELEGRAM_BOT_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = telegram.main(operation="unknown", TELEGRAM_BOT_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_chat = telegram.main(operation="send_message", TELEGRAM_BOT_TOKEN="token")
    missing_text = telegram.main(
        operation="send_message", chat_id="123", TELEGRAM_BOT_TOKEN="token"
    )
    missing_photo = telegram.main(
        operation="send_photo", chat_id="123", TELEGRAM_BOT_TOKEN="token"
    )
    missing_question = telegram.main(
        operation="send_poll", chat_id="123", TELEGRAM_BOT_TOKEN="token"
    )

    assert missing_chat["output"]["error"]["message"] == "Missing required chat_id"
    assert missing_text["output"]["error"]["message"] == "Missing required text"
    assert missing_photo["output"]["error"]["message"] == "Missing required photo_url"
    assert missing_question["output"]["error"]["message"] == "Missing required question"


def test_dry_run_preview_for_get_me():
    result = telegram.main(operation="get_me", TELEGRAM_BOT_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "get_me"
    assert preview["method"] == "POST"
    assert "/getMe" in preview["url"]


def test_dry_run_preview_for_send_message():
    result = telegram.main(
        operation="send_message",
        chat_id="123456",
        text="Hello Telegram!",
        TELEGRAM_BOT_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_message"
    assert preview["method"] == "POST"
    assert "/sendMessage" in preview["url"]
    assert preview["payload"]["chat_id"] == "123456"
    assert preview["payload"]["text"] == "Hello Telegram!"


def test_dry_run_preview_for_send_poll():
    result = telegram.main(
        operation="send_poll",
        chat_id="123456",
        question="What's your favorite color?",
        options="Red,Blue,Green",
        TELEGRAM_BOT_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_poll"
    assert preview["method"] == "POST"
    assert "/sendPoll" in preview["url"]
    assert preview["payload"]["question"] == "What's your favorite color?"
    assert preview["payload"]["options"] == ["Red", "Blue", "Green"]


def test_get_me_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"ok": True, "result": {"id": 123, "username": "test_bot"}},
    )
    fake_client = FakeClient(response=fake_response)

    result = telegram.main(
        operation="get_me",
        TELEGRAM_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == 123
    assert result["output"]["username"] == "test_bot"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert "/getMe" in url


def test_send_message_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={
            "ok": True,
            "result": {"message_id": 999, "text": "Hello Telegram!"},
        },
    )
    fake_client = FakeClient(response=fake_response)

    result = telegram.main(
        operation="send_message",
        chat_id="123456",
        text="Hello Telegram!",
        TELEGRAM_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["message_id"] == 999
    assert result["output"]["text"] == "Hello Telegram!"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert "/sendMessage" in url
    assert kwargs["json"]["text"] == "Hello Telegram!"


def test_send_photo_with_caption():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"ok": True, "result": {"message_id": 888}},
    )
    fake_client = FakeClient(response=fake_response)

    result = telegram.main(
        operation="send_photo",
        chat_id="123456",
        photo_url="https://example.com/photo.jpg",
        caption="A nice photo",
        TELEGRAM_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["message_id"] == 888
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert kwargs["json"]["photo"] == "https://example.com/photo.jpg"
    assert kwargs["json"]["caption"] == "A nice photo"


def test_api_error_handling():
    fake_response = DummyResponse(
        status_code=400,
        json_data={"ok": False, "description": "Chat not found"},
    )
    fake_client = FakeClient(response=fake_response)

    result = telegram.main(
        operation="send_message",
        chat_id="invalid",
        text="Test",
        TELEGRAM_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    exc = requests.exceptions.RequestException("Network error")
    exc.response = None
    fake_client = FakeClient(exc=exc)

    result = telegram.main(
        operation="get_me",
        TELEGRAM_BOT_TOKEN="token",
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

    result = telegram.main(
        operation="get_me",
        TELEGRAM_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
