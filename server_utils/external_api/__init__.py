"""Utilities for external API server definitions."""

from .content_decoder import auto_decode_response, decode_content
from .error_response import (
    api_error,
    error_output,
    error_response,
    missing_secret_error,
    validation_error,
)
from .form_generator import FormField, generate_form
from .google_auth import GoogleAuthManager
from .http_client import ExternalApiClient, HttpClientConfig
from .microsoft_auth import MicrosoftAuthManager
from .oauth_manager import OAuthManager, OAuthTokens
from .secret_validator import validate_api_key_with_endpoint, validate_secret
from .webhook_receiver import WebhookConfig, WebhookReceiver

__all__ = [
    "auto_decode_response",
    "decode_content",
    "error_output",
    "error_response",
    "missing_secret_error",
    "api_error",
    "validation_error",
    "ExternalApiClient",
    "HttpClientConfig",
    "OAuthManager",
    "OAuthTokens",
    "GoogleAuthManager",
    "MicrosoftAuthManager",
    "validate_secret",
    "validate_api_key_with_endpoint",
    "FormField",
    "generate_form",
    "WebhookConfig",
    "WebhookReceiver",
]
