# ruff: noqa: F821, F706
"""Demonstrates automatic mapping to a main() function."""

from html import escape


def render_row(label, value):
    if value in (None, ""):
        return ""
    return f"<p><strong>{escape(str(label))}:</strong> {escape(str(value))}</p>"


def main(name, greeting="Hello", topic="Viewer", user_agent=None, context=None):
    """Render a greeting using values drawn from the request."""
    message = f"{greeting}, {name}!"
    details = [
        "<html><body>",
        "<h1>Automatic main() mapping</h1>",
        render_row("Message", message),
        render_row("Topic", topic),
        render_row("User-Agent", user_agent or "(not provided)"),
        "<p>This template reads query parameters, request body values, and headers.</p>",
        "</body></html>",
    ]
    return {
        "output": "".join(details),
        "content_type": "text/html",
    }
