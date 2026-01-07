"""Utilities for external API server definitions."""

from .content_decoder import auto_decode_response, decode_content
from .credential_validator import CredentialValidator
from .executor import execute_json_request
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
from .limit_validator import (
    get_limit_info,
    validate_limit,
    validate_pagination_params,
)
from .microsoft_auth import MicrosoftAuthManager
from .oauth_manager import OAuthManager, OAuthTokens
from .operation_validator import OperationValidator
from .operation_dispatch import OperationDefinition, RequiredField, validate_and_build_payload
from .parameter_validator import ParameterValidator
from .preview_builder import PreviewBuilder
from .response_handler import ResponseHandler
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
    "execute_json_request",
    "OAuthManager",
    "OAuthTokens",
    "GoogleAuthManager",
    "MicrosoftAuthManager",
    "validate_secret",
    "validate_api_key_with_endpoint",
    "validate_limit",
    "validate_pagination_params",
    "get_limit_info",
    "FormField",
    "generate_form",
    "WebhookConfig",
    "WebhookReceiver",
    "CredentialValidator",
    "OperationValidator",
    "OperationDefinition",
    "RequiredField",
    "validate_and_build_payload",
    "ParameterValidator",
    "PreviewBuilder",
    "ResponseHandler",
]
