"""Tests for webhook receiver utilities."""

import hashlib
import hmac
import json

from server_utils.external_api import WebhookConfig, WebhookReceiver


def echo_handler(payload: dict) -> dict:
    return {"output": payload}


def test_valid_signature_processes_payload() -> None:
    config = WebhookConfig(secret="shh", signature_header="X-Test-Signature")
    receiver = WebhookReceiver(config)
    payload = json.dumps({"hello": "world"}).encode()

    signature = hmac.new(b"shh", payload, hashlib.sha256).hexdigest()
    headers = {config.signature_header: signature}

    result = receiver.process_webhook(payload, headers, echo_handler)

    assert result == {"output": {"hello": "world"}}


def test_invalid_signature_returns_error() -> None:
    config = WebhookConfig(secret="shh")
    receiver = WebhookReceiver(config)
    payload = b"{}"
    headers = {config.signature_header: "bad"}

    result = receiver.process_webhook(payload, headers, echo_handler)

    assert result["output"]["error"]["message"] == "Invalid webhook signature"
    assert result["output"]["error"]["type"] == "auth_error"


def test_invalid_json_returns_error() -> None:
    config = WebhookConfig(secret="shh")
    receiver = WebhookReceiver(config)
    payload = b"{invalid"
    headers = {
        config.signature_header: hmac.new(b"shh", payload, hashlib.sha256).hexdigest()
    }

    result = receiver.process_webhook(payload, headers, echo_handler)

    assert result["output"]["error"]["type"] == "validation_error"
