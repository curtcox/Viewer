"""Diagnostic extraction and formatting functions for gateway errors.

These functions extract and format diagnostic information from exceptions,
tracebacks, and error HTML to help debug gateway issues.
"""

import re
from html import escape


def format_exception_summary(exc: Exception) -> str:
    """Format an exception as a summary string.
    
    Args:
        exc: Exception to format
        
    Returns:
        Formatted exception summary (e.g., "ValueError: Invalid input")
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    return f"{exc_type}: {exc_msg}" if exc_msg else exc_type


def derive_exception_summary_from_traceback(error_detail: str | None) -> str | None:
    """Extract exception summary from the last line of a traceback.
    
    Args:
        error_detail: Traceback string
        
    Returns:
        Exception summary if found, None otherwise
    """
    if not isinstance(error_detail, str) or not error_detail.strip():
        return None

    lines = [line.strip() for line in error_detail.splitlines() if line.strip()]
    if not lines:
        return None

    last_line = lines[-1]
    if ":" not in last_line:
        return None

    return last_line


def extract_exception_summary_from_internal_error_html(html: str | None) -> str | None:
    """Extract exception summary from internal server error HTML.
    
    Args:
        html: HTML error page content
        
    Returns:
        Exception summary if found, None otherwise
    """
    if not isinstance(html, str) or not html:
        return None

    match = re.search(r"Exception:</strong>\s*([^<]+)", html)
    if not match:
        return None

    return match.group(1).strip() or None


def extract_stack_trace_list_from_internal_error_html(html: str | None) -> str | None:
    """Extract and format stack trace from internal server error HTML.
    
    Args:
        html: HTML error page content
        
    Returns:
        Formatted stack trace HTML if found, None otherwise
    """
    if not isinstance(html, str) or not html:
        return None

    exception_match = re.search(r"Exception:</strong>\s*([^<]+)", html)
    ol_match = re.search(r"(<ol[^>]*>.*?</ol>)", html, re.DOTALL)
    if not ol_match:
        return None

    exception_text = exception_match.group(1).strip() if exception_match else "Exception"
    ol_html = ol_match.group(1)
    return f"<div class=\"stack-trace\"><h2>Stack trace</h2><div><strong>{escape(exception_text)}</strong></div>{ol_html}</div>"


def safe_preview_request_details(request_details: dict) -> dict:
    """Create a safe preview of request details for display.
    
    Removes sensitive information like authorization headers.
    
    Args:
        request_details: Dictionary of request details
        
    Returns:
        Sanitized request details dictionary
    """
    preview = request_details.copy()
    
    # Remove sensitive headers
    if "headers" in preview and isinstance(preview["headers"], dict):
        headers = preview["headers"].copy()
        # Remove authorization and cookie headers
        headers.pop("Authorization", None)
        headers.pop("authorization", None)
        headers.pop("Cookie", None)
        headers.pop("cookie", None)
        preview["headers"] = headers
    
    return preview


def format_exception_detail(exc: Exception, *, debug_context: dict | None = None) -> str:
    """Format detailed exception information for debugging.
    
    Args:
        exc: Exception to format
        debug_context: Optional context information to include
        
    Returns:
        Formatted exception detail string
    """
    import traceback as tb
    
    lines = [
        f"Exception: {format_exception_summary(exc)}",
        "",
        "Traceback:",
        tb.format_exc(),
    ]
    
    if debug_context:
        lines.extend([
            "",
            "Debug Context:",
        ])
        for key, value in debug_context.items():
            lines.append(f"  {key}: {value!r}")
    
    return "\n".join(lines)
