"""Error handler functions for HTTP errors."""

from pathlib import Path
from flask import current_app, render_template, request

from alias_routing import is_potential_alias_path, try_alias_redirect
from cid_utils import serve_cid_content
from constants import RESERVED_ROUTES
from db_access import get_cid_by_path, rollback_session
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
    try_server_execution,
    try_server_execution_with_partial,
)


def get_existing_routes():
    """
    Get set of existing routes that should take precedence over server names.

    Returns:
        Set of reserved route paths
    """
    return RESERVED_ROUTES


def not_found_error(error):  # pylint: disable=unused-argument  # Required by Flask error handler
    """
    Custom 404 handler that checks CID table and server names for content.

    This handler tries to resolve 404s by checking if the path matches:
    1. An alias path - redirects to the alias target
    2. A server path - executes the server
    3. A versioned server path - executes the server with version
    4. A CID path - serves the CID content

    Args:
        error: The 404 error object

    Returns:
        Response object or rendered 404 template
    """
    path = request.path
    existing_routes = get_existing_routes()

    if is_potential_alias_path(path, existing_routes):
        alias_result = try_alias_redirect(path)
        if alias_result is not None:
            return alias_result

    if is_potential_server_path(path, existing_routes):
        server_result = try_server_execution(path)
        if server_result is not None:
            return server_result

    if is_potential_versioned_server_path(path, existing_routes):
        from .servers import get_server_definition_history

        server_result = try_server_execution_with_partial(path, get_server_definition_history)
        if server_result is not None:
            return server_result

    base_path = path.split('.')[0] if '.' in path else path
    cid_content = get_cid_by_path(base_path)
    if cid_content:
        result = serve_cid_content(cid_content, path)
        if result is not None:
            return result

    return render_template('404.html', path=path), 404


def internal_error(error):
    """
    Enhanced 500 error handler with comprehensive stack trace reporting.

    This handler builds a detailed stack trace with source links for project files
    and renders a comprehensive error page for debugging.

    Args:
        error: The exception that caused the 500 error

    Returns:
        Rendered 500 error template with stack trace
    """
    rollback_session()

    # Always try to build a comprehensive stack trace
    stack_trace = []
    exception = None
    exception_type = "Unknown Error"
    exception_message = "An unexpected error occurred"

    try:
        # Import here to avoid circular import and to allow for proper mocking in tests
        from routes.source import _get_tracked_paths
        from utils.stack_trace import build_stack_trace, extract_exception

        root_path = Path(current_app.root_path).resolve()

        # Get tracked paths for source linking
        try:
            tracked_paths = _get_tracked_paths(current_app.root_path)
        except Exception:  # pragma: no cover - defensive fallback when git unavailable  # pylint: disable=broad-except
            tracked_paths = frozenset()

        # Extract the exception and build stack trace
        exception = extract_exception(error)
        exception_type = type(exception).__name__
        exception_message = str(exception) if str(exception) else "No error message available"

        stack_trace = build_stack_trace(error, root_path, tracked_paths)

    except Exception as trace_error:  # pylint: disable=broad-exception-caught  # Fallback error handler
        # If stack trace building fails, create a minimal fallback
        try:
            import sys

            # Get the current exception info
            _, _, exc_traceback = sys.exc_info()
            if exc_traceback:
                # Create a basic stack trace as fallback
                stack_trace = [{
                    "display_path": "Error in stack trace generation",
                    "lineno": 0,
                    "function": "internal_error",
                    "code": f"Stack trace generation failed: {trace_error}\n\nOriginal error: {error}",
                    "source_link": None,
                    "is_separator": False,
                }]

            # Try to get basic info about the original error
            if not exception:
                exception = error
                exception_type = type(error).__name__
                exception_message = str(error) if str(error) else "Error occurred during error handling"

        except Exception:  # pylint: disable=broad-exception-caught  # Ultimate fallback for error handling
            # Ultimate fallback - just show basic error info
            stack_trace = [{
                "display_path": "Critical error handling failure",
                "lineno": 0,
                "function": "internal_error",
                "code": f"Both original error and error handling failed.\nOriginal error: {error}",
                "source_link": None,
                "is_separator": False,
            }]

    return (
        render_template(
            '500.html',
            stack_trace=stack_trace,
            exception_type=exception_type,
            exception_message=exception_message,
        ),
        500,
    )


__all__ = [
    'get_existing_routes',
    'not_found_error',
    'internal_error',
]
