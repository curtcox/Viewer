"""Shared utilities for route response handling."""

from flask import g
from typing import Literal


ResponseFormat = Literal["json", "xml", "csv", "html"]


def wants_structured_response() -> bool:
    """Check if the request wants a structured (non-HTML) response.

    Returns:
        True if the response format is JSON, XML, or CSV
        False if the response format is HTML or not specified

    Example:
        >>> if wants_structured_response():
        ...     return jsonify(data)
        >>> return render_template('page.html', data=data)
    """
    return getattr(g, "response_format", None) in {"json", "xml", "csv"}


def get_response_format() -> ResponseFormat:
    """Get the requested response format, defaulting to HTML.

    Returns:
        The response format string: "json", "xml", "csv", or "html"

    Example:
        >>> format = get_response_format()
        >>> if format == "json":
        ...     return jsonify(data)
    """
    return getattr(g, "response_format", "html")
