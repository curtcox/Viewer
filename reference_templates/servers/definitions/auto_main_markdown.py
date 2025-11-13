# ruff: noqa: F821, F706
"""Automatic main() mapping template for rendering Markdown content."""

from typing import Any

from cid_utils import _render_markdown_document


def _normalize_markdown(markdown_text: Any) -> str:
    """Coerce arbitrary input into normalized Markdown text."""

    if isinstance(markdown_text, bytes):
        text = markdown_text.decode("utf-8", "replace")
    else:
        text = str(markdown_text or "")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def main(markdown: Any = "", *, context=None):
    """Render Markdown text to HTML using the Viewer Markdown pipeline."""

    document = _render_markdown_document(_normalize_markdown(markdown))
    return {
        "output": document,
        "content_type": "text/html",
    }
