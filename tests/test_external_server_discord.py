import requests
from typing import Any

from reference_templates.servers.definitions import discord


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
    result = discord.main(dry_run=False)

    assert result["output"]["error"] == "Missing DISCORD_BOT_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = discord.main(operation="unknown", DISCORD_BOT_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_guild = discord.main(operation="get_guild", DISCORD_BOT_TOKEN="token")
    missing_channel = discord.main(operation="send_message", DISCORD_BOT_TOKEN="token")
    missing_content = discord.main(operation="send_message", channel_id="123", DISCORD_BOT_TOKEN="token")
    missing_channel_name = discord.main(operation="create_channel", guild_id="123", DISCORD_BOT_TOKEN="token")

    assert missing_guild["output"]["error"]["message"] == "Missing required guild_id"
    assert missing_channel["output"]["error"]["message"] == "Missing required channel_id"
    assert missing_content["output"]["error"]["message"] == "Missing required content"
    assert missing_channel_name["output"]["error"]["message"] == "Missing required channel_name"


def test_dry_run_preview_for_list_guilds():
    result = discord.main(operation="list_guilds", DISCORD_BOT_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_guilds"
    assert preview["method"] == "GET"
    assert "users/@me/guilds" in preview["url"]


def test_dry_run_preview_for_send_message():
    result = discord.main(
        operation="send_message",
        channel_id="123456",
        content="Hello Discord!",
        DISCORD_BOT_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "send_message"
    assert preview["method"] == "POST"
    assert "channels/123456/messages" in preview["url"]
    assert preview["payload"]["content"] == "Hello Discord!"


def test_dry_run_preview_for_create_channel():
    result = discord.main(
        operation="create_channel",
        guild_id="789",
        channel_name="new-channel",
        channel_type=0,
        DISCORD_BOT_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "create_channel"
    assert preview["method"] == "POST"
    assert "guilds/789/channels" in preview["url"]
    assert preview["payload"]["name"] == "new-channel"


def test_list_guilds_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data=[{"id": "123", "name": "Test Guild"}],
    )
    fake_client = FakeClient(response=fake_response)

    result = discord.main(
        operation="list_guilds",
        DISCORD_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"] == [{"id": "123", "name": "Test Guild"}]
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "GET"
    assert "users/@me/guilds" in url
    assert "Bot token" in kwargs["headers"]["Authorization"]


def test_send_message_success():
    fake_response = DummyResponse(
        status_code=200,
        json_data={"id": "999", "content": "Hello Discord!"},
    )
    fake_client = FakeClient(response=fake_response)

    result = discord.main(
        operation="send_message",
        channel_id="123456",
        content="Hello Discord!",
        DISCORD_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "999"
    assert result["output"]["content"] == "Hello Discord!"
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert "channels/123456/messages" in url
    assert kwargs["json"]["content"] == "Hello Discord!"


def test_api_error_handling():
    fake_response = DummyResponse(
        status_code=403,
        json_data={"message": "Missing Access"},
    )
    fake_client = FakeClient(response=fake_response)

    result = discord.main(
        operation="list_guilds",
        DISCORD_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 403


def test_request_exception_handling():
    exc = requests.exceptions.RequestException("Network error")
    exc.response = None
    fake_client = FakeClient(exc=exc)

    result = discord.main(
        operation="list_guilds",
        DISCORD_BOT_TOKEN="token",
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

    result = discord.main(
        operation="list_guilds",
        DISCORD_BOT_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
