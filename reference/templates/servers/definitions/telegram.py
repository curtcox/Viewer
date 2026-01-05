# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "send_message",
    "send_photo",
    "send_document",
    "get_updates",
    "get_me",
    "edit_message",
    "delete_message",
    "send_poll",
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
        message = "Telegram API error"
        if isinstance(data, dict):
            message = data.get("description", message)
        return error_output(message, status_code=response.status_code, details=data)

    # Telegram returns {ok: true, result: ...}
    if isinstance(data, dict) and data.get("ok"):
        return {"output": data.get("result", data)}

    return {"output": data}


def main(
    *,
    operation: str = "get_me",
    chat_id: str = "",
    text: str = "",
    message_id: str = "",
    photo_url: str = "",
    document_url: str = "",
    caption: str = "",
    question: str = "",
    options: str = "",  # Comma-separated poll options
    limit: int = 100,
    offset: int = 0,
    TELEGRAM_BOT_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Telegram Bot API for messaging and bot management."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not TELEGRAM_BOT_TOKEN:
        return error_output(
            "Missing TELEGRAM_BOT_TOKEN",
            status_code=401,
            details="Provide a bot token to authenticate Telegram API calls.",
        )

    if normalized_operation in ("send_message", "send_photo", "send_document", "send_poll") and not chat_id:
        return validation_error("Missing required chat_id", field="chat_id")

    if normalized_operation == "send_message" and not text:
        return validation_error("Missing required text", field="text")

    if normalized_operation == "send_photo" and not photo_url:
        return validation_error("Missing required photo_url", field="photo_url")

    if normalized_operation == "send_document" and not document_url:
        return validation_error("Missing required document_url", field="document_url")

    if normalized_operation in ("edit_message", "delete_message") and not message_id:
        return validation_error("Missing required message_id", field="message_id")

    if normalized_operation in ("edit_message", "delete_message") and not chat_id:
        return validation_error("Missing required chat_id", field="chat_id")

    if normalized_operation == "send_poll" and not question:
        return validation_error("Missing required question", field="question")

    if normalized_operation == "send_poll" and not options:
        return validation_error("Missing required options", field="options")

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    api_url = base_url
    method = "POST"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "get_me":
        api_url = f"{base_url}/getMe"
    elif normalized_operation == "send_message":
        api_url = f"{base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
    elif normalized_operation == "send_photo":
        api_url = f"{base_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
        }
        if caption:
            payload["caption"] = caption
    elif normalized_operation == "send_document":
        api_url = f"{base_url}/sendDocument"
        payload = {
            "chat_id": chat_id,
            "document": document_url,
        }
        if caption:
            payload["caption"] = caption
    elif normalized_operation == "get_updates":
        api_url = f"{base_url}/getUpdates"
        payload = {
            "limit": limit,
            "offset": offset,
        }
    elif normalized_operation == "edit_message":
        api_url = f"{base_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
    elif normalized_operation == "delete_message":
        api_url = f"{base_url}/deleteMessage"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
    elif normalized_operation == "send_poll":
        api_url = f"{base_url}/sendPoll"
        poll_options = [opt.strip() for opt in options.split(",")]
        payload = {
            "chat_id": chat_id,
            "question": question,
            "options": poll_options,
        }

    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            url=api_url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview}}

    api_client = client or _DEFAULT_CLIENT

    try:
        response = api_client.request(
            method=method,
            url=api_url,
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
