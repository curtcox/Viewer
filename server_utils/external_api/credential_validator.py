"""Validate required credentials/secrets for external API servers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .error_response import error_output


class CredentialValidator:
    """Validate required credentials/secrets.
    
    This class provides utilities to validate that all required secrets are
    provided before making API calls, reducing duplication across servers.
    
    Example:
        >>> error = CredentialValidator.require_secrets(
        ...     AWS_ACCESS_KEY_ID="my-key",
        ...     AWS_SECRET_ACCESS_KEY="my-secret"
        ... )
        >>> error is None
        True
        >>> error = CredentialValidator.require_secrets(
        ...     AWS_ACCESS_KEY_ID="",
        ...     AWS_SECRET_ACCESS_KEY="my-secret"
        ... )
        >>> "Missing AWS_ACCESS_KEY_ID" in error["output"]["error"]
        True
    """

    @staticmethod
    def require_secrets(**secrets: str) -> Optional[Dict[str, Any]]:
        """Validate that all required secrets are provided.
        
        Args:
            **secrets: Keyword arguments where key is secret name and value is the secret
            
        Returns:
            Error dict if any secret is missing, None if all present
            
        Example:
            error = CredentialValidator.require_secrets(
                API_KEY=api_key,
                API_SECRET=api_secret
            )
            if error:
                return error
        """
        for name, value in secrets.items():
            if not value:
                return error_output(f"Missing {name}", status_code=401)
        return None

    @staticmethod
    def require_secret(secret_value: str, secret_name: str) -> Optional[Dict[str, Any]]:
        """Validate that a single required secret is provided.
        
        Args:
            secret_value: The secret value to check
            secret_name: Name of the secret for error messages
            
        Returns:
            Error dict if secret is missing, None if present
            
        Example:
            error = CredentialValidator.require_secret(api_key, "API_KEY")
            if error:
                return error
        """
        if not secret_value:
            return error_output(f"Missing {secret_name}", status_code=401)
        return None

    @staticmethod
    def require_one_of(**secrets: str) -> Optional[Dict[str, Any]]:
        """Validate that at least one of the provided secrets is present.
        
        Args:
            **secrets: Keyword arguments where key is secret name and value is the secret
            
        Returns:
            Error dict if all secrets are missing, None if at least one is present
            
        Example:
            error = CredentialValidator.require_one_of(
                API_KEY=api_key,
                ACCESS_TOKEN=access_token
            )
            if error:
                return error
        """
        if not any(secrets.values()):
            secret_names = " or ".join(secrets.keys())
            return error_output(
                f"Missing required authentication: provide {secret_names}",
                status_code=401,
            )
        return None
