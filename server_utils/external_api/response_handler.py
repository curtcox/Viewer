"""Standardized handling of HTTP responses and exceptions for external API servers."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import requests

from .error_response import error_output


class ResponseHandler:
    """Standardized handling of HTTP responses and exceptions.
    
    This class provides utilities for consistent error handling and response
    parsing across external server definitions.
    
    Example:
        >>> try:
        ...     response = requests.get(url)
        ... except requests.RequestException as exc:
        ...     return ResponseHandler.handle_request_exception(exc)
    """

    @staticmethod
    def handle_request_exception(exc: requests.RequestException) -> Dict[str, Any]:
        """Standardized handling of requests exceptions.
        
        Args:
            exc: The RequestException that was raised
            
        Returns:
            Error response dict
            
        Example:
            try:
                response = api_client.get(url, headers=headers)
            except requests.RequestException as exc:
                return ResponseHandler.handle_request_exception(exc)
        """
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Request failed",
            status_code=status or 500,
            details=str(exc),
        )

    @staticmethod
    def handle_json_response(
        response: requests.Response,
        error_message_extractor: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> Dict[str, Any]:
        """Parse JSON response and handle errors consistently.
        
        Args:
            response: The HTTP response object
            error_message_extractor: Optional function to extract error message from response data
            
        Returns:
            Success dict with data or error dict
            
        Example:
            response = api_client.get(url, headers=headers)
            return ResponseHandler.handle_json_response(response)
            
            # With custom error extractor
            def get_error(data):
                return data.get("error", {}).get("message", "API error")
            return ResponseHandler.handle_json_response(response, get_error)
        """
        try:
            data = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response",
                status_code=getattr(response, "status_code", 500),
                details=getattr(response, "text", "")[:500],  # Limit details length
            )

        if not getattr(response, "ok", False):
            message = "API error"
            if error_message_extractor and callable(error_message_extractor):
                extracted = error_message_extractor(data)
                if extracted:  # Use extracted message only if it's truthy
                    message = extracted
            return error_output(
                message,
                status_code=response.status_code,
                response=data,
            )

        return {"output": data}

    @staticmethod
    def check_response_ok(response: requests.Response) -> bool:
        """Safely check if response indicates success.
        
        Args:
            response: The HTTP response object
            
        Returns:
            True if response is successful, False otherwise
            
        Example:
            response = api_client.get(url, headers=headers)
            if not ResponseHandler.check_response_ok(response):
                return error_output("Request failed")
        """
        return getattr(response, "ok", False)

    @staticmethod
    def extract_json_or_error(
        response: requests.Response,
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Extract JSON from response or return error.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Tuple of (data, error) where one is always None
            
        Example:
            data, error = ResponseHandler.extract_json_or_error(response)
            if error:
                return error
            return {"output": data}
        """
        try:
            data = response.json()
            return data, None
        except ValueError:
            error = error_output(
                "Invalid JSON response",
                status_code=getattr(response, "status_code", None),
                details=getattr(response, "text", None),
            )
            return None, error
