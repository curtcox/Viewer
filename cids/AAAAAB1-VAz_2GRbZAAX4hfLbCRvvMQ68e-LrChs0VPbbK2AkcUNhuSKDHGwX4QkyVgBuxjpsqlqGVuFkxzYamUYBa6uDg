# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Response transform for JSONPlaceholder API gateway.

Transforms JSONPlaceholder API responses into formatted HTML with clickable links.
"""

from html import escape


def transform_response(response_details: dict, context: dict) -> dict:
    """Transform JSONPlaceholder API response to formatted HTML.

    Args:
        response_details: Dict containing status_code, headers, content, text, json, request_path
        context: Full server execution context

    Returns:
        Dict with output (HTML) and content_type
    """
    request_path = response_details.get("request_path", "")
    status_code = response_details.get("status_code", 200)
    json_data = response_details.get("json")

    # If not JSON or error, return raw response
    if json_data is None:
        text = response_details.get("text", "")
        if status_code >= 400:
            return {
                "output": _render_error_page(status_code, text),
                "content_type": "text/html",
            }
        return {
            "output": text,
            "content_type": response_details.get("headers", {}).get(
                "Content-Type", "text/plain"
            ),
        }

    # Format JSON as HTML with links
    html_output = _render_json_as_html(json_data, request_path)

    return {
        "output": html_output,
        "content_type": "text/html",
    }


def _render_error_page(status_code: int, message: str) -> str:
    """Render an error page."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Error {status_code}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #1e1e1e; color: #d4d4d4; }}
        .error {{ background: #3d1f1f; border-left: 4px solid #f44; padding: 1rem; border-radius: 4px; }}
        h1 {{ color: #f44; }}
        a {{ color: #4ec9b0; }}
    </style>
</head>
<body>
    <div class="error">
        <h1>Error {status_code}</h1>
        <p>{escape(message)}</p>
    </div>
    <p><a href="/gateway/jsonplaceholder">Back to JSONPlaceholder</a></p>
</body>
</html>"""


def _render_json_as_html(data, request_path: str) -> str:
    """Render JSON data as formatted HTML with embedded links."""
    # Build breadcrumb from path
    breadcrumb = _build_breadcrumb(request_path)

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '    <meta charset="utf-8">',
        "    <title>JSONPlaceholder - " + escape(request_path or "/") + "</title>",
        "    <style>",
        "        body { font-family: 'Courier New', monospace; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; background: #1e1e1e; color: #d4d4d4; }",
        "        pre { background: #252526; padding: 1.5rem; border-radius: 8px; overflow-x: auto; line-height: 1.5; }",
        "        .json-key { color: #9cdcfe; }",
        "        .json-string { color: #ce9178; }",
        "        .json-number { color: #b5cea8; }",
        "        .json-boolean { color: #569cd6; }",
        "        .json-null { color: #569cd6; }",
        "        .json-link { color: #4ec9b0; text-decoration: underline; cursor: pointer; }",
        "        .json-link:hover { color: #4fc3f7; }",
        "        h1 { color: #4ec9b0; font-size: 1.5rem; }",
        "        .breadcrumb { color: #858585; margin-bottom: 1rem; }",
        "        .breadcrumb a { color: #4ec9b0; text-decoration: none; }",
        "        .breadcrumb a:hover { text-decoration: underline; }",
        "        .nav { margin-bottom: 1rem; }",
        "        .nav a { color: #4ec9b0; margin-right: 1rem; text-decoration: none; }",
        "        .nav a:hover { text-decoration: underline; }",
        "    </style>",
        "</head>",
        "<body>",
        f'    <div class="breadcrumb">{breadcrumb}</div>',
        '    <div class="nav">',
        '        <a href="/gateway/jsonplaceholder/posts">Posts</a>',
        '        <a href="/gateway/jsonplaceholder/users">Users</a>',
        '        <a href="/gateway/jsonplaceholder/comments">Comments</a>',
        '        <a href="/gateway/jsonplaceholder/albums">Albums</a>',
        '        <a href="/gateway/jsonplaceholder/photos">Photos</a>',
        '        <a href="/gateway/jsonplaceholder/todos">Todos</a>',
        "    </div>",
        "    <h1>API Response</h1>",
        "    <pre>",
    ]

    # Format JSON with syntax highlighting and links
    formatted_json = _format_json_with_links(data, indent=0)
    html_parts.append(formatted_json)

    html_parts.extend(
        [
            "    </pre>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(html_parts)


def _build_breadcrumb(request_path: str) -> str:
    """Build breadcrumb navigation from path."""
    parts = ["<a href=\"/gateway/jsonplaceholder\">jsonplaceholder</a>"]

    if request_path:
        path_parts = request_path.strip("/").split("/")
        current_path = "/gateway/jsonplaceholder"
        for part in path_parts:
            if part:
                current_path += "/" + part
                parts.append(f'<a href="{escape(current_path)}">{escape(part)}</a>')

    return " / ".join(parts)


def _format_json_with_links(obj, indent: int = 0) -> str:
    """Format JSON with syntax highlighting and convert userId to links."""
    indent_str = "  " * indent

    if obj is None:
        return "<span class='json-null'>null</span>"

    if isinstance(obj, bool):
        return f"<span class='json-boolean'>{str(obj).lower()}</span>"

    if isinstance(obj, (int, float)):
        return f"<span class='json-number'>{obj}</span>"

    if isinstance(obj, str):
        return f"<span class='json-string'>\"{escape(obj)}\"</span>"

    if isinstance(obj, list):
        if not obj:
            return "[]"

        items = []
        for item in obj:
            formatted_item = _format_json_with_links(item, indent + 1)
            items.append(f"{indent_str}  {formatted_item}")

        return "[\n" + ",\n".join(items) + f"\n{indent_str}]"

    if isinstance(obj, dict):
        if not obj:
            return "{}"

        items = []
        for key, value in obj.items():
            formatted_value = _format_json_with_links(value, indent + 1)

            # Special handling for userId - make it a link
            if key == "userId" and isinstance(value, (int, str)):
                user_link = f"/gateway/jsonplaceholder/users/{value}"
                formatted_value = f"<a href='{escape(user_link)}' class='json-link'>{formatted_value}</a>"

            # Special handling for id in posts/comments context - could link to self
            if key == "postId" and isinstance(value, (int, str)):
                post_link = f"/gateway/jsonplaceholder/posts/{value}"
                formatted_value = f"<a href='{escape(post_link)}' class='json-link'>{formatted_value}</a>"

            if key == "albumId" and isinstance(value, (int, str)):
                album_link = f"/gateway/jsonplaceholder/albums/{value}"
                formatted_value = f"<a href='{escape(album_link)}' class='json-link'>{formatted_value}</a>"

            items.append(
                f"{indent_str}  <span class='json-key'>\"{escape(str(key))}\"</span>: {formatted_value}"
            )

        return "{\n" + ",\n".join(items) + f"\n{indent_str}" + "}"

    return f"<span class='json-string'>\"{escape(str(obj))}\"</span>"
