"""Generic webhook receiver utilities for external services."""

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any, Callable, Dict

from .error_response import error_response


@dataclass
class WebhookConfig:
    """Webhook validation configuration."""

    secret: str
    signature_header: str = "X-Signature"
    signature_algorithm: str = "sha256"
    signature_prefix: str = ""  # e.g., "sha256=" for GitHub


class WebhookReceiver:
    """Generic webhook receiver with signature validation."""

    def __init__(self, config: WebhookConfig):
        self.config = config

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature using the configured algorithm."""

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
