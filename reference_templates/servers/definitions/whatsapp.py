# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "send_message",
    "send_template",
    "get_message",
    "mark_as_read",
    "upload_media",
    "get_media",
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
        "auth": "bearer_token",
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
        message = "WhatsApp API error"
        if isinstance(data, dict) and "error" in data:
            error_data = data["error"]
            message = error_data.get("message", message)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "send_message",
    to: str = "",
    message_type: str = "text",
    text_body: str = "",
    template_name: str = "",
    template_language: str = "en",
    message_id: str = "",
    media_url: str = "",
    media_id: str = "",
    caption: str = "",
    WHATSAPP_ACCESS_TOKEN: str = "",
    WHATSAPP_PHONE_NUMBER_ID: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with WhatsApp Business API for messaging."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not WHATSAPP_ACCESS_TOKEN:
        return error_output(
            "Missing WHATSAPP_ACCESS_TOKEN",
            status_code=401,
            details="Provide an access token to authenticate WhatsApp API calls.",
        )

    if not WHATSAPP_PHONE_NUMBER_ID:
        return error_output(
            "Missing WHATSAPP_PHONE_NUMBER_ID",
            status_code=401,
            details="Provide a phone number ID to identify the WhatsApp Business account.",
        )

    if normalized_operation in ("send_message", "send_template") and not to:
        return validation_error("Missing required to", field="to")

    if normalized_operation == "send_message" and not text_body:
        return validation_error("Missing required text_body", field="text_body")

    if normalized_operation == "send_template" and not template_name:
        return validation_error("Missing required template_name", field="template_name")

    if normalized_operation in ("get_message", "mark_as_read") and not message_id:
        return validation_error("Missing required message_id", field="message_id")

    base_url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    api_url = base_url
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "send_message":
        api_url = f"{base_url}/messages"
        method = "POST"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": message_type,
            "text": {"body": text_body},
        }
    elif normalized_operation == "send_template":
        api_url = f"{base_url}/messages"
        method = "POST"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": template_language},
            },
        }
    elif normalized_operation == "get_message":
        api_url = f"https://graph.facebook.com/v18.0/{message_id}"
    elif normalized_operation == "mark_as_read":
        api_url = f"{base_url}/messages"
        method = "POST"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
    elif normalized_operation == "upload_media":
        api_url = f"{base_url}/media"
        method = "POST"
        # Note: Actual file upload would require multipart/form-data
        payload = {
            "messaging_product": "whatsapp",
            "type": message_type,
        }
    elif normalized_operation == "get_media":
        api_url = f"https://graph.facebook.com/v18.0/{media_id}"

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
