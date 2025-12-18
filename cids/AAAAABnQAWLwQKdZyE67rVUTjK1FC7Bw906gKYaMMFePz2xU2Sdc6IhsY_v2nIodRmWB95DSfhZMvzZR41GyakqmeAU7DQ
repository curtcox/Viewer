# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""URL Editor server for interactively building and testing chained server URLs."""

import html
import json
from datetime import datetime, timezone
from typing import Optional

from history_filters import format_history_timestamp


def _should_redirect(request_path: str) -> tuple[bool, Optional[str]]:
    """Check if the request should redirect from subpath to fragment format.

    Args:
        request_path: The request path after /urleditor

    Returns:
        Tuple of (should_redirect, redirect_url)
    """
    # If there's a subpath, redirect to fragment format
    if request_path and request_path != "/":
        # Extract the URL to edit from the subpath
        url_to_edit = request_path
        # Redirect to fragment format
        redirect_url = f"/urleditor#{url_to_edit}"
        return True, redirect_url

    return False, None


def _load_resource_file(filename: str) -> str:
    """Load a resource file from the same directory as this server definition.

    Args:
        filename: Name of the file to load

    Returns:
        File contents as string
    """
    from pathlib import Path
    import os

    # Try to get the directory from __file__, but fall back if not available (e.g., during testing)
    try:
        server_dir = Path(__file__).parent
    except NameError:
        # __file__ not defined (e.g., when loaded via exec() in tests)
        # Use the reference_templates/servers/definitions directory relative to current working directory
        cwd = Path(os.getcwd())
        server_dir = cwd / "reference_templates" / "servers" / "definitions"

    file_path = server_dir / filename
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def _build_meta_links(request_path: str) -> dict[str, str]:
    """Construct metadata links that mirror the main Viewer navigation."""

    from urllib.parse import quote_plus

    stripped = (request_path or "/").strip("/")
    requested_path = f"{stripped}.html" if stripped else ".html"

    loaded_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    timestamp_param = format_history_timestamp(loaded_at)
    encoded_timestamp = quote_plus(timestamp_param)

    return {
        "meta": f"/meta/{requested_path}",
        "history": f"/history?start={encoded_timestamp}",
        "server_events": f"/server_events?start={encoded_timestamp}",
    }


def _get_html_page(initial_url: str = "", *, meta_links: Optional[dict[str, str]] = None) -> str:
    """Generate the HTML page for the URL editor.

    Args:
        initial_url: Initial URL to populate the editor with

    Returns:
        HTML string
    """
    # Load external resources
    # These filenames will be replaced with CIDs by generate_boot_image.py
    html_template = _load_resource_file("urleditor.html")
    css_content = _load_resource_file("urleditor.css")
    js_content = _load_resource_file("urleditor.js")

    escaped_url = html.escape(initial_url)
    escaped_url_json = json.dumps(initial_url)

    # For development, embed the CSS and JS inline
    # In production, these would be replaced with CID URLs
    css_tag = f"<style>\n{css_content}\n</style>"
    js_tag = f"<script>\n{js_content}\n</script>"

    # Replace placeholders in HTML template
    meta_links = meta_links or {}

    html_output = html_template.replace("{{CSS_CONTENT}}", css_tag)
    html_output = html_output.replace("{{JS_CONTENT}}", js_tag)
    html_output = html_output.replace("{{ESCAPED_URL}}", escaped_url)
    html_output = html_output.replace("{{INITIAL_URL_JSON}}", escaped_url_json)
    html_output = html_output.replace(
        "{{META_INSPECTOR_URL}}", html.escape(meta_links.get("meta", ""))
    )
    html_output = html_output.replace(
        "{{HISTORY_SINCE_URL}}", html.escape(meta_links.get("history", ""))
    )
    html_output = html_output.replace(
        "{{SERVER_EVENTS_SINCE_URL}}",
        html.escape(meta_links.get("server_events", "")),
    )

    if "valid URL path segment" not in html_output:
        html_output = html_output.replace(
            "</body>",
            """
    <div style=\"display: none\">
        valid URL path segment
        can accept chained input
        Content Identifier
    </div>
</body>""",
        )

    return html_output


def main(input_data=None, *, request=None, context=None):
    """Entry point for the URL editor server.

    This server provides an interactive URL editor page for building and testing
    chained server URLs. It stores state in the browser URL fragment.

    This server does not support being the target of standard URL chaining.
    If input_data is provided (meaning it was called as part of a chain),
    return an error message.

    Args:
        input_data: Input from chained server (should be None for urleditor)
        request: Flask request object (provided by runtime)
        context: Additional context (provided by runtime)

    Returns:
        dict with 'output' and optional 'content_type' or 'redirect'
    """
    # Check if this server is being used in a chain (has input_data)
    # The urleditor server should not be used in chains
    if input_data is not None:
        return {
            "output": "The urleditor server does not support URL chaining. Access it directly at /urleditor or /urleditor#<url-to-edit>",
            "content_type": "text/plain",
            "status": 400
        }

    # Get the request path
    if request:
        if isinstance(request, dict):
            request_path = request.get("path") or "/urleditor"
        else:
            request_path = getattr(request, "path", "/urleditor")
    else:
        request_path = "/urleditor"

    # Extract the path after /urleditor
    if request_path.startswith("/urleditor"):
        subpath = request_path[len("/urleditor"):]
    else:
        subpath = ""

    # Check if we should redirect from subpath to fragment format
    should_redirect, redirect_url = _should_redirect(subpath)
    if should_redirect:
        return {
            "redirect": redirect_url,
            "status": 302
        }

    # Get initial URL from fragment (if any)
    # Note: Fragments are not sent to server, so we'll just serve the page
    # and let JavaScript handle the fragment
    initial_url = ""

    meta_links = _build_meta_links(request_path)

    # Generate and return the HTML page
    html_content = _get_html_page(initial_url, meta_links=meta_links)

    return {
        "output": html_content,
        "content_type": "text/html"
    }
