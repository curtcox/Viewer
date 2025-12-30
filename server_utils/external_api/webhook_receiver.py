"""Generic webhook receiver utilities for external services."""

from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict

from .error_response import error_response


@dataclass
class WebhookConfig:
    """Webhook validation configuration."""

    secret: str
    signature_header: str = "X-Signature"
    signature_algorithm: str = "sha256"
    signature_prefix: str = ""  # e.g., "sha256=" for GitHub
    timestamp_tolerance_seconds: int = 300


class WebhookReceiver:
    """Generic webhook receiver with signature validation."""

    def __init__(self, config: WebhookConfig):
        self.config = config

    def _validate_stripe_signature(self, payload: bytes, signature_header_value: str) -> bool:
        parts: Dict[str, list[str]] = {}
        for token in signature_header_value.split(","):
            token = token.strip()
            if not token or "=" not in token:
                continue
            key, value = token.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or not value:
                continue
            parts.setdefault(key, []).append(value)

        timestamp_values = parts.get("t")
        v1_signatures = parts.get("v1")
        if not timestamp_values or not v1_signatures:
            return False

        try:
            timestamp = int(timestamp_values[0])
        except ValueError:
            return False

        now = int(time.time())
        if abs(now - timestamp) > self.config.timestamp_tolerance_seconds:
            return False

        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            self.config.secret.encode(),
            signed_payload,
            getattr(hashlib, self.config.signature_algorithm),
        ).hexdigest()

        return any(hmac.compare_digest(expected, candidate) for candidate in v1_signatures)

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature using the configured algorithm."""

        if self.config.signature_header.lower() == "stripe-signature":
            return self._validate_stripe_signature(payload, signature)

        expected = hmac.new(
            self.config.secret.encode(),
            payload,
            getattr(hashlib, self.config.signature_algorithm),
        ).hexdigest()

        if self.config.signature_prefix:
            expected = f"{self.config.signature_prefix}{expected}"

        return hmac.compare_digest(expected, signature)

    def process_webhook(
        self,
        payload: bytes,
        headers: Dict[str, str],
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate the webhook and hand off to the provided handler."""

        signature = headers.get(self.config.signature_header, "")
        if not self.validate_signature(payload, signature):
            return error_response(
                message="Invalid webhook signature",
                error_type="auth_error",
                status_code=401,
            )

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            return error_response(
                message=f"Invalid JSON payload: {exc}",
                error_type="validation_error",
                status_code=400,
            )

        return handler(data)
