# readonly_middleware.py
"""Middleware for handling read-only mode restrictions."""

from functools import wraps
from typing import Any, Callable

from flask import abort, request

from readonly_config import ReadOnlyConfig


def block_in_readonly_mode(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to block state-changing operations in read-only mode.

    Returns 405 Method Not Allowed when in read-only mode.

    Args:
        f: The route function to wrap

    Returns:
        Wrapped function that checks read-only mode
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if ReadOnlyConfig.is_read_only_mode():
            abort(405, description="Operation not allowed in read-only mode")
        return f(*args, **kwargs)
    return decorated_function


def is_state_changing_request() -> bool:
    """Check if the current request is attempting to change state.

    Returns:
        True if request would change state, False otherwise
    """
    # State-changing HTTP methods
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return True

    # Check for specific state-changing paths (GET requests that change state)
    path = request.path
    state_changing_paths = [
        '/delete',
        '/enable',
        '/disable',
        '/toggle',
    ]

    for pattern in state_changing_paths:
        if pattern in path:
            return True

    return False
