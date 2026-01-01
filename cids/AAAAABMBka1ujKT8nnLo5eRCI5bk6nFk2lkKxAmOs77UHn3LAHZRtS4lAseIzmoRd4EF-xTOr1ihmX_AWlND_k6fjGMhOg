# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Response transform for JSONPlaceholder API gateway.

Transforms JSONPlaceholder API responses into formatted HTML with clickable links.
Uses external Jinja templates from the gateway config.
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
    
    # Get template resolver from context
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured in gateway config")

    # If not JSON or error, handle appropriately
    if json_data is None:
        text = response_details.get("text", "")
        if status_code >= 400:
            template = resolve_template("jsonplaceholder_error.html")
            html = template.render(status_code=status_code, message=text)
            return {
                "output": html,
                "content_type": "text/html",
            }
        return {
            "output": text,
            "content_type": response_details.get("headers", {}).get(
                "Content-Type", "text/plain"
            ),
        }

    # Format JSON with links and render with template
    breadcrumb = _build_breadcrumb(request_path)
    formatted_json = _format_json_with_links(json_data, indent=0)
    
    template = resolve_template("jsonplaceholder_data.html")
    html = template.render(
        request_path=request_path,
        breadcrumb=breadcrumb,
        formatted_json=formatted_json,
    )

    return {
        "output": html,
        "content_type": "text/html",
    }


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
