"""Build standardized preview objects for dry-run mode in external API servers."""

from __future__ import annotations

from typing import Any, Dict, Optional


class PreviewBuilder:
    """Build standardized preview objects for dry-run mode.
    
    This class helps standardize preview/dry-run responses across external
    server definitions, reducing duplication and ensuring consistency.
    
    Example:
        >>> preview = PreviewBuilder.build(
        ...     operation="list_issues",
        ...     url="https://api.github.com/repos/owner/repo/issues",
        ...     method="GET",
        ...     auth_type="Bearer Token"
        ... )
        >>> preview["operation"]
        'list_issues'
        >>> preview["method"]
        'GET'
    """

    @staticmethod
    def build(
        operation: str,
        url: str,
        method: str,
        auth_type: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Build a preview object showing what would be executed.
        
        Args:
            operation: The operation being performed
            url: The URL that would be called
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            auth_type: Authentication method description
            params: Optional query parameters
            payload: Optional request body
            headers: Optional request headers (sensitive values should be redacted)
            **extra: Additional server-specific fields to include
            
        Returns:
            Dictionary with preview information
            
        Example:
            preview = PreviewBuilder.build(
                operation="create_issue",
                url="https://api.github.com/repos/owner/repo/issues",
                method="POST",
                auth_type="Bearer Token",
                payload={"title": "Bug report", "body": "Description"},
                headers={"Accept": "application/vnd.github+json"}
            )
        """
        preview: Dict[str, Any] = {
            "operation": operation,
            "url": url,
            "method": method,
            "auth": auth_type,
        }

        if params:
            preview["params"] = params

        if payload:
            preview["payload"] = payload

        if headers:
            # Redact sensitive headers
            safe_headers = _redact_sensitive_headers(headers)
            preview["headers"] = safe_headers

        if extra:
            preview.update(extra)

        return preview

    @staticmethod
    def dry_run_response(preview: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap a preview in a standard dry-run response format.
        
        Args:
            preview: The preview object from build()
            
        Returns:
            Complete dry-run response dictionary
            
        Example:
            preview = PreviewBuilder.build(...)
            return PreviewBuilder.dry_run_response(preview)
        """
        return {
            "output": {
                "preview": preview,
                "message": "Dry run - no API call made",
            }
        }


def _redact_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive information from headers.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Dictionary with sensitive values redacted
    """
    sensitive_keys = {
        "authorization",
        "x-api-key",
        "api-token",
        "x-auth-token",
        "cookie",
        "x-csrf-token",
        "x-api-token",
        "api_key",
        "secret",
        "password",
    }

    return {
        key: "***" if key.lower() in sensitive_keys else value
        for key, value in headers.items()
    }
