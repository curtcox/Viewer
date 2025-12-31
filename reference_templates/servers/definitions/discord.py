# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "list_guilds",
    "get_guild",
    "list_channels",
    "get_channel",
    "send_message",
    "list_messages",
    "create_channel",
    "delete_message",
}


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    params: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "bot_token",
    }

    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload

    return preview


def _parse_json_response(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )


def _handle_response(response: requests.Response) -> Dict[str, Any]:
    data = _parse_json_response(response)
    if "output" in data:
        return data

    if not response.ok:
        message = "Discord API error"
        if isinstance(data, dict):
            message = data.get("message", message)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "list_guilds",
    guild_id: str = "",
    channel_id: str = "",
    message_id: str = "",
    channel_name: str = "",
    channel_type: int = 0,
    content: str = "",
    limit: int = 50,
    DISCORD_BOT_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Discord guilds, channels, and messages."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not DISCORD_BOT_TOKEN:
        return error_output(
            "Missing DISCORD_BOT_TOKEN",
            status_code=401,
            details="Provide a bot token to authenticate Discord API calls.",
        )

    if normalized_operation in ("get_guild", "list_channels") and not guild_id:
        return validation_error("Missing required guild_id", field="guild_id")

    if normalized_operation in ("get_channel", "send_message", "list_messages", "delete_message") and not channel_id:
        return validation_error("Missing required channel_id", field="channel_id")

    if normalized_operation == "send_message" and not content:
        return validation_error("Missing required content", field="content")

    if normalized_operation == "create_channel" and not guild_id:
        return validation_error("Missing required guild_id for create_channel", field="guild_id")

    if normalized_operation == "create_channel" and not channel_name:
        return validation_error("Missing required channel_name", field="channel_name")

    if normalized_operation == "delete_message" and not message_id:
        return validation_error("Missing required message_id", field="message_id")

    base_url = "https://discord.com/api/v10"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    url = base_url
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "list_guilds":
        url = f"{base_url}/users/@me/guilds"
    elif normalized_operation == "get_guild":
        url = f"{base_url}/guilds/{guild_id}"
    elif normalized_operation == "list_channels":
        url = f"{base_url}/guilds/{guild_id}/channels"
    elif normalized_operation == "get_channel":
        url = f"{base_url}/channels/{channel_id}"
    elif normalized_operation == "send_message":
        url = f"{base_url}/channels/{channel_id}/messages"
        method = "POST"
        payload = {"content": content}
    elif normalized_operation == "list_messages":
        url = f"{base_url}/channels/{channel_id}/messages"
        params = {"limit": limit}
    elif normalized_operation == "create_channel":
        url = f"{base_url}/guilds/{guild_id}/channels"
        method = "POST"
        payload = {
            "name": channel_name,
            "type": channel_type,
        }
    elif normalized_operation == "delete_message":
        url = f"{base_url}/channels/{channel_id}/messages/{message_id}"
        method = "DELETE"

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview}}

    api_client = client or _DEFAULT_CLIENT

    try:
        response = api_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=payload,
            timeout=timeout,
        )
        return _handle_response(response)
    except requests.exceptions.RequestException as exc:
        status_code = exc.response.status_code if exc.response else None
        return error_output(
            f"Request failed: {exc}",
            status_code=status_code,
            details=str(exc),
        )
