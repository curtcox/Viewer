"""Error capture and formatting for server execution."""

import json
import traceback
import html
from pathlib import Path
from typing import Any, Dict, Optional

from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid
from db_access import create_cid_record, get_cid_by_path
from flask import Response, current_app, make_response, render_template, url_for
from werkzeug.routing import BuildError


def _extract_server_error_lineno(exc: Exception) -> Optional[int]:
    lineno = getattr(exc, "lineno", None)
    if isinstance(lineno, int) and lineno > 0:
        return lineno

    traceback_obj = getattr(exc, "__traceback__", None)
    if traceback_obj is None:
        return None

    try:
        frames = traceback.extract_tb(traceback_obj)
    except Exception:  # pragma: no cover - defensive fallback
        return None

    server_frame = None
    for frame in frames:
        if frame.filename == "<string>":
            server_frame = frame

    if (
        server_frame
        and isinstance(server_frame.lineno, int)
        and server_frame.lineno > 0
    ):
        return server_frame.lineno

    return None


def _render_server_source_with_highlight(code_text: str, highlight_lineno: int) -> str:
    lines = code_text.splitlines()
    output_lines: list[str] = []
    for index, line in enumerate(lines, start=1):
        escaped = html.escape(line)
        css_class = "server-source-line"
        if index == highlight_lineno:
            css_class += " highlight"
        output_lines.append(
            f'<span class="{css_class}" data-line="{index}">'
            f'<span class="server-source-lineno">{index:4d}</span> {escaped}</span>'
        )
    return "\n".join(output_lines)


def _wrap_highlighted_lines(
    highlighted_html: str, highlight_lineno: Optional[int]
) -> str:
    lines = highlighted_html.splitlines()
    output_lines: list[str] = []
    for index, line in enumerate(lines, start=1):
        css_class = "server-source-line"
        if highlight_lineno is not None and index == highlight_lineno:
            css_class += " highlight"
        output_lines.append(
            f'<span class="{css_class}" data-line="{index}">'
            f'<span class="server-source-lineno">{index:4d}</span> {line}</span>'
        )
    return "\n".join(output_lines)


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
    server_source_css = None
    if code_text:
        highlight_lineno = _extract_server_error_lineno(exc)
        mapped_lineno = highlight_lineno - 1 if highlight_lineno is not None else None
        if mapped_lineno is not None and not 1 <= mapped_lineno <= len(
            code_text.splitlines()
        ):
            mapped_lineno = None

        highlighted_inner, syntax_css = highlight_source(
            code_text,
            filename=f"{server_name or 'server'}.py",
            fallback_lexer="python",
        )
        if highlighted_inner is not None:
            highlighted_code = _wrap_highlighted_lines(highlighted_inner, mapped_lineno)
        else:
            highlighted_code = None

        server_source_css = (
            ".server-source-line{display:block;white-space:pre;}"
            ".server-source-lineno{display:inline-block;color:#6c757d;margin-right:.75rem;}"
            ".server-source-line.highlight{background-color:rgba(255,193,7,.25);"
            "border-left:4px solid #ffc107;padding-left:.5rem;}"
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

    return render_template(
        "500.html",
        stack_trace=stack_trace,
        exception_type=exception_type,
        exception_message=message,
        highlighted_server_code=highlighted_code,
        server_definition=code_text,
        syntax_css=syntax_css,
        server_source_css=server_source_css,
        server_args_json=args_json,
        server_name=server_name,
        server_definition_url=server_definition_url,
    )


def _handle_execution_exception(
    exc: Exception,
    code: str,
    args: Dict[str, Any],
    server_name: Optional[str],
    *,
    external_calls: Optional[list[dict[str, Any]]] = None,
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
    try:
        output_bytes = response.get_data()
    except Exception:  # pragma: no cover - defensive fallback
        output_bytes = b""

    try:
        cid_value = format_cid(generate_cid(output_bytes))
        cid_record_path = cid_path(cid_value)
        existing = get_cid_by_path(cid_record_path) if cid_record_path else None
        if cid_record_path and not existing:
            create_cid_record(cid_value, output_bytes)

        from server_execution.invocation_tracking import (  # pylint: disable=cyclic-import
            create_server_invocation_record,
        )

        create_server_invocation_record(
            server_name or "", cid_value, external_calls=external_calls
        )
    except Exception:  # pragma: no cover - best-effort logging
        pass
    return response
