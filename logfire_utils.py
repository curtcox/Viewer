"""Utility module for optional logfire integration.

This module provides a safe wrapper around logfire that gracefully handles
cases where logfire is not installed, making it an optional dependency.
"""

from typing import Any, Callable, TypeVar

# Type variable for function decorators
F = TypeVar('F', bound=Callable[..., Any])

# Try to import logfire, but make it optional
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    logfire = None  # type: ignore[assignment, misc]
    LOGFIRE_AVAILABLE = False


def _noop_instrument(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """No-op decorator when logfire is not available.
    
    This decorator does nothing - it just returns the function unchanged.
    """
    def decorator(func: F) -> F:
        return func
    return decorator


def instrument(name: str, *, extract_args: bool = False, record_return: bool = False) -> Callable[[F], F]:
    """Instrument a function with logfire, or use no-op if logfire is not available.
    
    Args:
        name: Instrumentation name/template
        extract_args: Whether to extract arguments
        record_return: Whether to record return value
        
    Returns:
        Decorator function that instruments the target function
    """
    if LOGFIRE_AVAILABLE and logfire is not None:
        return logfire.instrument(name, extract_args=extract_args, record_return=record_return)
    return _noop_instrument()
