# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Response transform for HRX archive gateway.

Transforms HRX server responses to fix relative URLs and render markdown.
"""

import re
from html import escape


def transform_response(response_details: dict, context: dict) -> dict:
    """Transform HRX response with URL fixing and markdown rendering.

    Args:
        response_details: Dict containing status_code, headers, content, text, json, request_path
        context: Full server execution context

    Returns:
        Dict with output and content_type
    """
    request_path = response_details.get("request_path", "")
    status_code = response_details.get("status_code", 200)
    text = response_details.get("text", "")
    content_type = response_details.get("headers", {}).get("Content-Type", "text/plain")

    # Parse the path to get CID and file path
    path_parts = request_path.strip("/").split("/", 1)
    archive_cid = path_parts[0] if path_parts else ""
    file_path = path_parts[1] if len(path_parts) > 1 else ""

    if status_code >= 400:
        return {
            "output": _render_error_page(archive_cid, file_path, text or "File not found"),
            "content_type": "text/html",
        }

    # If this is a directory listing (no file path or ends with /), render navigation
    if not file_path or file_path.endswith("/"):
        # Try to parse as file list
        if text and not text.strip().startswith("<"):
            return {
                "output": _render_directory(archive_cid, file_path, text),
                "content_type": "text/html",
            }

    # Determine file type from path
    if file_path.endswith(".md"):
        # Render markdown as HTML
        html_content = _render_markdown(text, archive_cid, file_path)
        return {
            "output": html_content,
            "content_type": "text/html",
        }

    if file_path.endswith(".html") or file_path.endswith(".htm"):
        # Fix relative URLs in HTML
        fixed_html = _fix_relative_urls(text, archive_cid, file_path)
        return {
            "output": fixed_html,
            "content_type": "text/html",
        }

    # For CSS, JS, images, etc. - pass through with URL fixes if text-based
    if file_path.endswith(".css"):
        fixed_css = _fix_css_urls(text, archive_cid, file_path)
        return {
            "output": fixed_css,
            "content_type": "text/css",
        }

    # Plain text or other files - wrap in HTML viewer
    if "text" in content_type or file_path.endswith((".txt", ".json", ".xml", ".py", ".js")):
        return {
            "output": _render_text_file(text, archive_cid, file_path),
            "content_type": "text/html",
        }

    # Binary files - pass through
    return {
        "output": response_details.get("content", b""),
        "content_type": content_type,
    }


def _render_error_page(archive_cid: str, file_path: str, message: str) -> str:
    """Render an error page."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HRX Error</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #1a1a2e; color: #eee; }}
        .error {{ background: #3d1f1f; border-left: 4px solid #f44; padding: 1rem; border-radius: 4px; }}
        h1 {{ color: #f44; }}
        a {{ color: #4ec9b0; }}
        code {{ background: #252536; padding: 0.2rem 0.4rem; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="error">
        <h1>Error</h1>
        <p>{escape(message)}</p>
        <p>Archive: <code>{escape(archive_cid)}</code></p>
        <p>Path: <code>{escape(file_path or '/')}</code></p>
    </div>
    <p><a href="/gateway/hrx/{escape(archive_cid)}">Back to archive root</a></p>
</body>
</html>"""


def _render_directory(archive_cid: str, current_path: str, file_list_text: str) -> str:
    """Render a directory listing."""
    files = [f.strip() for f in file_list_text.split("\n") if f.strip()]

    # Build breadcrumb
    breadcrumb = _build_breadcrumb(archive_cid, current_path)

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '    <meta charset="utf-8">',
        f"    <title>HRX: {escape(current_path or '/')}</title>",
        "    <style>",
        "        body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #1a1a2e; color: #eee; }",
        "        h1 { color: #4ec9b0; }",
        "        .breadcrumb { color: #858585; margin-bottom: 1rem; }",
        "        .breadcrumb a { color: #4ec9b0; text-decoration: none; }",
        "        .breadcrumb a:hover { text-decoration: underline; }",
        "        .file-list { list-style: none; padding: 0; }",
        "        .file-list li { padding: 0.5rem; border-bottom: 1px solid #333; }",
        "        .file-list a { color: #9cdcfe; text-decoration: none; }",
        "        .file-list a:hover { text-decoration: underline; }",
        "        .file-icon { margin-right: 0.5rem; }",
        "        code { font-family: 'Courier New', monospace; background: #252536; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.9rem; }",
        "    </style>",
        "</head>",
        "<body>",
        f'    <div class="breadcrumb">{breadcrumb}</div>',
        f"    <h1>Archive Contents</h1>",
        f"    <p>CID: <code>{escape(archive_cid)}</code></p>",
        '    <ul class="file-list">',
    ]

    # Add parent directory link if not at root
    if current_path:
        parent = "/".join(current_path.rstrip("/").split("/")[:-1])
        parent_link = f"/gateway/hrx/{archive_cid}/{parent}" if parent else f"/gateway/hrx/{archive_cid}"
        html_parts.append(f'        <li><span class="file-icon">..</span><a href="{escape(parent_link)}">Parent Directory</a></li>')

    for file in files:
        file_link = f"/gateway/hrx/{archive_cid}/{file}"
        icon = "" if "/" in file or file.endswith("/") else ""
        html_parts.append(f'        <li><span class="file-icon">{icon}</span><a href="{escape(file_link)}">{escape(file)}</a></li>')

    html_parts.extend([
        "    </ul>",
        "</body>",
        "</html>",
    ])

    return "\n".join(html_parts)


def _build_breadcrumb(archive_cid: str, current_path: str) -> str:
    """Build breadcrumb navigation."""
    parts = [f'<a href="/gateway/hrx/{escape(archive_cid)}">archive</a>']

    if current_path:
        path_parts = current_path.strip("/").split("/")
        accumulated = f"/gateway/hrx/{archive_cid}"
        for part in path_parts:
            if part:
                accumulated += "/" + part
                parts.append(f'<a href="{escape(accumulated)}">{escape(part)}</a>')

    return " / ".join(parts)


def _render_markdown(text: str, archive_cid: str, file_path: str) -> str:
    """Render markdown as HTML with fixed links."""
    import markdown

    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc"])
    html_content = md.convert(text)

    # Fix relative links in the rendered HTML
    html_content = _fix_relative_urls(html_content, archive_cid, file_path)

    breadcrumb = _build_breadcrumb(archive_cid, file_path)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{escape(file_path)}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #1a1a2e; color: #eee; line-height: 1.6; }}
        .breadcrumb {{ color: #858585; margin-bottom: 1rem; }}
        .breadcrumb a {{ color: #4ec9b0; text-decoration: none; }}
        h1, h2, h3 {{ color: #4ec9b0; }}
        a {{ color: #9cdcfe; }}
        code {{ font-family: 'Courier New', monospace; background: #252536; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #252536; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
        pre code {{ padding: 0; background: none; }}
        blockquote {{ border-left: 4px solid #4ec9b0; margin: 0; padding-left: 1rem; color: #aaa; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #333; padding: 0.5rem; text-align: left; }}
        th {{ background: #252536; }}
    </style>
</head>
<body>
    <div class="breadcrumb">{breadcrumb}</div>
    {html_content}
</body>
</html>"""


def _render_text_file(text: str, archive_cid: str, file_path: str) -> str:
    """Render a text file with syntax highlighting wrapper."""
    breadcrumb = _build_breadcrumb(archive_cid, file_path)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{escape(file_path)}</title>
    <style>
        body {{ font-family: 'Courier New', monospace; max-width: 1000px; margin: 2rem auto; padding: 0 1rem; background: #1a1a2e; color: #eee; }}
        .breadcrumb {{ font-family: system-ui, -apple-system, sans-serif; color: #858585; margin-bottom: 1rem; }}
        .breadcrumb a {{ color: #4ec9b0; text-decoration: none; }}
        pre {{ background: #252536; padding: 1rem; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="breadcrumb">{breadcrumb}</div>
    <pre>{escape(text)}</pre>
</body>
</html>"""


def _fix_relative_urls(html: str, archive_cid: str, file_path: str) -> str:
    """Fix relative URLs to point to the gateway path."""
    # Get the directory of the current file
    if "/" in file_path:
        current_dir = "/".join(file_path.split("/")[:-1])
    else:
        current_dir = ""

    base_path = f"/gateway/hrx/{archive_cid}"
    if current_dir:
        base_path += "/" + current_dir

    # Fix href attributes
    def fix_href(match):
        attr = match.group(1)  # href or src
        quote = match.group(2)  # quote character
        url = match.group(3)

        # Skip absolute URLs, protocol-relative URLs, anchors, data URIs
        if url.startswith(("http://", "https://", "//", "#", "data:", "javascript:", "mailto:")):
            return match.group(0)

        # Handle relative URLs
        if url.startswith("/"):
            # Absolute path within archive
            fixed_url = f"/gateway/hrx/{archive_cid}{url}"
        else:
            # Relative path
            fixed_url = f"{base_path}/{url}"

        return f'{attr}={quote}{fixed_url}{quote}'

    # Match href="..." or src="..." with various quote styles
    pattern = r'(href|src)=(["\'])([^"\']+)\2'
    return re.sub(pattern, fix_href, html, flags=re.IGNORECASE)


def _fix_css_urls(css: str, archive_cid: str, file_path: str) -> str:
    """Fix url() references in CSS."""
    # Get the directory of the current file
    if "/" in file_path:
        current_dir = "/".join(file_path.split("/")[:-1])
    else:
        current_dir = ""

    base_path = f"/gateway/hrx/{archive_cid}"
    if current_dir:
        base_path += "/" + current_dir

    def fix_url(match):
        url = match.group(1).strip("'\"")

        # Skip absolute URLs, data URIs
        if url.startswith(("http://", "https://", "//", "data:")):
            return match.group(0)

        # Handle relative URLs
        if url.startswith("/"):
            fixed_url = f"/gateway/hrx/{archive_cid}{url}"
        else:
            fixed_url = f"{base_path}/{url}"

        return f'url("{fixed_url}")'

    # Match url(...) in CSS
    pattern = r'url\(([^)]+)\)'
    return re.sub(pattern, fix_url, css, flags=re.IGNORECASE)
