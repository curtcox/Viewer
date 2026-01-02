"""Shared error response formatting for external servers."""

from typing import Any, Dict, Optional


def error_output(
    message: str,
    *,
    status_code: Optional[int] = None,
    response: Optional[Any] = None,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build a structured error payload under the ``output`` key.

    Returns a dictionary shaped like::

        {"output": {"error": "message", ...}}

    Optional fields are included only when provided.
    """

    payload: Dict[str, Any] = {"error": message}
    if status_code is not None:
        payload["status_code"] = status_code
    if response is not None:
        payload["response"] = response
    if details is not None:
        payload["details"] = details
    return {"output": payload}


def error_response(
    message: str,
    error_type: str = "api_error",
    status_code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a typed error payload used by shared validators."""

    payload: Dict[str, Any] = {"message": message, "type": error_type}
    if status_code is not None:
        payload["status_code"] = status_code
    if details:
        payload["details"] = details
    return {"output": {"error": payload}, "content_type": "application/json"}


def missing_secret_error(secret_name: str) -> Dict[str, Any]:
    """Error response for missing API secret."""

    return error_response(
        message=f"Missing required secret: {secret_name}",
        error_type="auth_error",
        details={"secret_name": secret_name},
    )


def api_error(
    message: str,
    status_code: Optional[int] = None,
    response_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Error response for API call failure."""

    details = {"response": response_body[:500]} if response_body else None
    return error_response(
        message=message,
        error_type="api_error",
        status_code=status_code,
        details=details,
    )


def validation_error(
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Error response for validation failure."""

    error_details: Dict[str, Any] = {}
    if field:
        error_details["field"] = field
    if details:
        error_details.update(details)

    return error_response(
        message=message,
        error_type="validation_error",
        details=error_details if error_details else None,
    )
