"""Error capture and formatting for server execution."""

import json
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Response, current_app, make_response, render_template, url_for
from werkzeug.routing import BuildError


def _render_execution_error_html(
    exc: Exception,
    code: str,
    args: Dict[str, Any],
    server_name: Optional[str],
) -> str:
    """Render an HTML error page for exceptions raised during server execution."""

    from routes.source import _get_tracked_paths
    from syntax_highlighting import highlight_source
    from utils.stack_trace import build_stack_trace, extract_exception

    root_path = Path(current_app.root_path).resolve()

    # Get tracked paths for source linking
    try:
        tracked_paths = _get_tracked_paths(current_app.root_path)
    except Exception:  # pragma: no cover - defensive fallback when git unavailable  # pylint: disable=broad-except
        tracked_paths = frozenset()

    exception = extract_exception(exc)
    exception_type = type(exception).__name__
    raw_message = str(exception)
    message = raw_message if raw_message else "No error message available"
    stack_trace = build_stack_trace(exc, root_path, tracked_paths)

    code_text = code if isinstance(code, str) else ""
    highlighted_code = None
    syntax_css = None
    if code_text:
        highlighted_code, syntax_css = highlight_source(
            code_text,
            filename=f"{server_name or 'server'}.py",
            fallback_lexer="python",
        )

    server_definition_url: Optional[str]
    if server_name:
        try:
            server_definition_url = url_for("main.view_server", server_name=server_name)
        except (RuntimeError, ValueError, BuildError):
            # Handle routing errors when outside request context or in test environments
            server_definition_url = None
    else:
        server_definition_url = None

    def _stringify(value: Any) -> str:
        try:
            return str(value)
        except (ValueError, TypeError):
            # Fall back to repr for non-stringifiable values
            return repr(value)

    try:
        args_json = json.dumps(
            args,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_stringify,
        )
    except (TypeError, ValueError):
        # Handle JSON serialization errors
        args_json = _stringify(args)

    html: str = render_template(
        "500.html",
        stack_trace=stack_trace,
        exception_type=exception_type,
        exception_message=message,
        highlighted_server_code=highlighted_code,
        server_definition=code_text,
        syntax_css=syntax_css,
        server_args_json=args_json,
        server_name=server_name,
        server_definition_url=server_definition_url,
    )
    return html


def _handle_execution_exception(
    exc: Exception, code: str, args: Dict[str, Any], server_name: Optional[str]
) -> Response:
    try:
        html_content = _render_execution_error_html(exc, code, args, server_name)
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    except Exception:  # pylint: disable=broad-exception-caught
        # Last-resort fallback: catch all exceptions including Jinja TemplateError, BuildError, etc.
        # This is essential to prevent unhandled exceptions when the error page itself fails to render.
        text = (
            str(exc)
            + "\n\n"
            + traceback.format_exc()
            + "\n\n"
            + code
            + "\n\n"
            + str(args)
        )
        response = make_response(text)
        response.headers["Content-Type"] = "text/plain"

    response.status_code = 500
    return response
