# ruff: noqa: F821, F706
from typing import Any, Dict, Optional

import requests

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


_SUPPORTED_OPERATIONS = {
    "send_sms",
    "list_messages",
    "get_message",
    "make_call",
    "list_calls",
    "get_call",
    "send_whatsapp",
    "list_available_numbers",
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
        "auth": "basic_auth",
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
        message = "Twilio API error"
        if isinstance(data, dict):
            message = data.get("message", message)
        return error_output(message, status_code=response.status_code, details=data)

    return {"output": data}


def main(
    *,
    operation: str = "send_sms",
    to: str = "",
    from_: str = "",
    body: str = "",
    message_sid: str = "",
    call_sid: str = "",
    url: str = "",
    country_code: str = "US",
    limit: int = 20,
    TWILIO_ACCOUNT_SID: str = "",
    TWILIO_AUTH_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Interact with Twilio messaging, calling, and phone number APIs."""

    normalized_operation = operation.lower()

    if normalized_operation not in _SUPPORTED_OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    if not TWILIO_ACCOUNT_SID:
        return error_output(
            "Missing TWILIO_ACCOUNT_SID",
            status_code=401,
            details="Provide an account SID to authenticate Twilio API calls.",
        )

    if not TWILIO_AUTH_TOKEN:
        return error_output(
            "Missing TWILIO_AUTH_TOKEN",
            status_code=401,
            details="Provide an auth token to authenticate Twilio API calls.",
        )

    if normalized_operation in ("send_sms", "send_whatsapp", "make_call") and not to:
        return validation_error("Missing required to", field="to")

    if normalized_operation in ("send_sms", "send_whatsapp") and not body:
        return validation_error("Missing required body", field="body")

    if normalized_operation in ("send_sms", "send_whatsapp", "make_call") and not from_:
        return validation_error("Missing required from_", field="from_")

    if normalized_operation == "make_call" and not url:
        return validation_error("Missing required url (TwiML URL)", field="url")

    if normalized_operation == "get_message" and not message_sid:
        return validation_error("Missing required message_sid", field="message_sid")

    if normalized_operation == "get_call" and not call_sid:
        return validation_error("Missing required call_sid", field="call_sid")

    base_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}"
    api_url = base_url
    method = "GET"
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    if normalized_operation == "send_sms":
        api_url = f"{base_url}/Messages.json"
        method = "POST"
        payload = {
            "To": to,
            "From": from_,
            "Body": body,
        }
    elif normalized_operation == "list_messages":
        api_url = f"{base_url}/Messages.json"
        params = {"PageSize": limit}
    elif normalized_operation == "get_message":
        api_url = f"{base_url}/Messages/{message_sid}.json"
    elif normalized_operation == "make_call":
        api_url = f"{base_url}/Calls.json"
        method = "POST"
        payload = {
            "To": to,
            "From": from_,
            "Url": url,
        }
    elif normalized_operation == "list_calls":
        api_url = f"{base_url}/Calls.json"
        params = {"PageSize": limit}
    elif normalized_operation == "get_call":
        api_url = f"{base_url}/Calls/{call_sid}.json"
    elif normalized_operation == "send_whatsapp":
        api_url = f"{base_url}/Messages.json"
        method = "POST"
        # WhatsApp messages require whatsapp: prefix
        to_number = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        from_number = from_ if from_.startswith("whatsapp:") else f"whatsapp:{from_}"
        payload = {
            "To": to_number,
            "From": from_number,
            "Body": body,
        }
    elif normalized_operation == "list_available_numbers":
        api_url = f"{base_url}/AvailablePhoneNumbers/{country_code}/Local.json"
        params = {"PageSize": limit}

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
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            params=params,
            data=payload,
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
