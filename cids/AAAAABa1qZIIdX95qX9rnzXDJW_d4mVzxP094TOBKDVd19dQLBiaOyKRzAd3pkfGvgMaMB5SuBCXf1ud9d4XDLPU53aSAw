# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()


_ENDPOINT_MAP = {
    "get_me": "getMe",
    "send_message": "sendMessage",
    "send_photo": "sendPhoto",
    "send_document": "sendDocument",
    "get_updates": "getUpdates",
    "edit_message": "editMessageText",
    "delete_message": "deleteMessage",
    "send_poll": "sendPoll",
}

_OPERATIONS = {
    "get_me": OperationDefinition(),
    "send_message": OperationDefinition(
        required=(RequiredField("chat_id"), RequiredField("text")),
        payload_builder=lambda chat_id, text, **_: {"chat_id": chat_id, "text": text},
    ),
    "send_photo": OperationDefinition(
        required=(RequiredField("chat_id"), RequiredField("photo_url")),
        payload_builder=lambda chat_id, photo_url, caption, **_: {
            "chat_id": chat_id,
            "photo": photo_url,
            **({"caption": caption} if caption else {}),
        },
    ),
    "send_document": OperationDefinition(
        required=(RequiredField("chat_id"), RequiredField("document_url")),
        payload_builder=lambda chat_id, document_url, caption, **_: {
            "chat_id": chat_id,
            "document": document_url,
            **({"caption": caption} if caption else {}),
        },
    ),
    "get_updates": OperationDefinition(
        payload_builder=lambda limit, offset, **_: {"limit": limit, "offset": offset},
    ),
    "edit_message": OperationDefinition(
        required=(RequiredField("chat_id"), RequiredField("message_id")),
        payload_builder=lambda chat_id, message_id, text, **_: {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        },
    ),
    "delete_message": OperationDefinition(
        required=(RequiredField("chat_id"), RequiredField("message_id")),
        payload_builder=lambda chat_id, message_id, **_: {
            "chat_id": chat_id,
            "message_id": message_id,
        },
    ),
    "send_poll": OperationDefinition(
        required=(
            RequiredField("chat_id"),
            RequiredField("question"),
            RequiredField("options"),
        ),
        payload_builder=lambda chat_id, question, options, **_: {
            "chat_id": chat_id,
            "question": question,
            "options": [opt.strip() for opt in options.split(",")],
        },
    ),
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


def _telegram_error_message(_response: requests.Response, data: Any) -> str:
    if isinstance(data, dict):
        return data.get("description", "Telegram API error")
    return "Telegram API error"


def _telegram_success_parser(response: requests.Response, data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        if not data.get("ok", True):
            return error_output(
                data.get("description", "Telegram API error"),
                status_code=response.status_code,
                details=data,
            )
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

    if not TELEGRAM_BOT_TOKEN:
        return error_output(
            "Missing TELEGRAM_BOT_TOKEN",
            status_code=401,
            details="Provide a bot token to authenticate Telegram API calls.",
        )

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    method = "POST"
    params: Optional[Dict[str, Any]] = None
    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        chat_id=chat_id,
        text=text,
        message_id=message_id,
        photo_url=photo_url,
        document_url=document_url,
        caption=caption,
        question=question,
        options=options,
        limit=limit,
        offset=offset,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    endpoint = _ENDPOINT_MAP.get(operation, operation)
    api_url = f"{base_url}/{endpoint}"

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=api_url,
            method=method,
            params=params,
            payload=payload,
        )
        return {"output": {"preview": preview}}

    api_client = client or _DEFAULT_CLIENT

    return execute_json_request(
        api_client,
        method,
        api_url,
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_telegram_error_message,
        success_parser=_telegram_success_parser,
        request_error_message="Request failed",
        include_exception_in_message=True,
    )
