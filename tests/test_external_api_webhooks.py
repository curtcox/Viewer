"""Tests for webhook receiver utilities."""

import hashlib
import hmac
import json
import time

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


def test_stripe_signature_validates_with_timestamp_and_payload() -> None:
    secret = "whsec_test"
    config = WebhookConfig(secret=secret, signature_header="Stripe-Signature")
    receiver = WebhookReceiver(config)
    payload = json.dumps({"id": "evt_123"}).encode()

    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    header_value = f"t={timestamp},v1={signature}"

    result = receiver.process_webhook(payload, {"Stripe-Signature": header_value}, echo_handler)

    assert result == {"output": {"id": "evt_123"}}


def test_stripe_signature_accepts_any_matching_v1() -> None:
    secret = "whsec_test"
    config = WebhookConfig(secret=secret, signature_header="Stripe-Signature")
    receiver = WebhookReceiver(config)
    payload = b"{}"

    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    header_value = f"t={timestamp},v1=deadbeef,v1={signature}"

    result = receiver.process_webhook(payload, {"Stripe-Signature": header_value}, echo_handler)

    assert result == {"output": {}}


def test_stripe_signature_rejects_invalid_timestamp() -> None:
    config = WebhookConfig(secret="whsec_test", signature_header="Stripe-Signature")
    receiver = WebhookReceiver(config)
    payload = b"{}"

    header_value = "t=notanint,v1=abc"

    result = receiver.process_webhook(payload, {"Stripe-Signature": header_value}, echo_handler)

    assert result["output"]["error"]["message"] == "Invalid webhook signature"
    assert result["output"]["error"]["type"] == "auth_error"


def test_stripe_signature_rejects_outside_tolerance() -> None:
    secret = "whsec_test"
    config = WebhookConfig(
        secret=secret,
        signature_header="Stripe-Signature",
        timestamp_tolerance_seconds=300,
    )
    receiver = WebhookReceiver(config)
    payload = b"{}"

    timestamp = int(time.time()) - 301
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    header_value = f"t={timestamp},v1={signature}"

    result = receiver.process_webhook(payload, {"Stripe-Signature": header_value}, echo_handler)

    assert result["output"]["error"]["message"] == "Invalid webhook signature"
    assert result["output"]["error"]["type"] == "auth_error"
