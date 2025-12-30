"""Validate API secrets before making calls."""

from typing import Any, Callable, Dict, Optional

import requests

from .error_response import api_error, missing_secret_error, validation_error


def validate_secret(
    secret_value: str,
    secret_name: str,
    validator: Optional[Callable[[str], bool]] = None,
) -> Optional[Dict[str, Any]]:
    """Validate a secret value and return an error payload if invalid."""

    if not secret_value:
        return missing_secret_error(secret_name)

    if validator and not validator(secret_value):
        return validation_error(f"Invalid {secret_name} format")

    return None


def validate_api_key_with_endpoint(
    api_key: str,
    validation_url: str,
    headers_builder: Callable[[str], Dict[str, str]],
    secret_name: str = "API_KEY",
) -> Optional[Dict[str, Any]]:
    """Validate an API key by calling a lightweight validation endpoint."""

    if not api_key:
        return missing_secret_error(secret_name)

    try:
        headers = headers_builder(api_key)
        response = requests.get(validation_url, headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        # Network or validation endpoint issues should not block main calls
        return None

    if response.status_code == 401:
        return api_error(
            message=f"Invalid or expired {secret_name}",
            status_code=401,
        )

    if response.status_code == 403:
        return api_error(
            message=f"Insufficient permissions for {secret_name}",
            status_code=403,
        )

    return None
