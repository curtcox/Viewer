# ruff: noqa: F821, F706
"""Send messages to Slack using chat.postMessage."""

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output


_DEFAULT_CLIENT = ExternalApiClient()


def main(
    text: str = "Hello from Viewer!",
    channel: str = "#general",
    *,
    SLACK_BOT_TOKEN: str,
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Send a message to Slack.

    Args:
        text: Message body to send.
        channel: Channel ID or name.
        SLACK_BOT_TOKEN: Slack bot token with `chat:write` scope.
        dry_run: When true, do not call the Slack API and return the request payload instead.
        timeout: Request timeout in seconds.
    """
    api_client = client or _DEFAULT_CLIENT

    if not SLACK_BOT_TOKEN:
        return error_output(
            "Missing SLACK_BOT_TOKEN",
            status_code=401,
            details="Provide a bot token with chat:write scope.",
        )

    payload = {"channel": channel, "text": text}

    if dry_run:
        return {
            "output": {
                "preview": payload,
                "message": "Dry run - no API call made",
            }
        }

    try:
        response = api_client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Slack request failed", status_code=status, details=str(exc)
        )

    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text,
        )

    if not data.get("ok"):
        return error_output(
            data.get("error", "Slack API call failed"),
            status_code=response.status_code,
            response=data,
        )

    return {"output": data}
