"""Utilities for rendering syntax-highlighted code snippets."""

from __future__ import annotations

from typing import Optional

from pygments import highlight
from pygments.formatters import HtmlFormatter  # pylint: disable=no-name-in-module  # HtmlFormatter exists
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound


def highlight_source(
    content: str,
    *,
    filename: Optional[str] = None,
    fallback_lexer: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return highlighted HTML and CSS for the provided source content.

    Args:
        content: The textual source to highlight.
        filename: Optional filename used to infer the lexer.
        fallback_lexer: Optional lexer name to use when the filename
            cannot be resolved. When omitted, plain text rendering is
            used.

    Returns:
        A tuple of ``(highlighted_html, syntax_css)``. Either value can be
        ``None`` if highlighting is unavailable.
    """

    if content is None:
        return None, None

    lexer = None

    if filename:
        try:
            lexer = get_lexer_for_filename(filename, content)
        except ClassNotFound:
            lexer = None

    if lexer is None and fallback_lexer:
        try:
            lexer = get_lexer_by_name(fallback_lexer)
        except ClassNotFound:
            lexer = None

    if lexer is None:
        lexer = TextLexer()

    try:
        formatter = HtmlFormatter(style="default", nowrap=True)
        highlighted = highlight(content, lexer, formatter)
        css = formatter.get_style_defs(".codehilite")
        return highlighted, css
    except (ValueError, TypeError, AttributeError):
        # Handle pygments errors gracefully
        return None, None
