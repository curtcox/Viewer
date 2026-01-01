# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Response transform for HRX archive gateway.

Transforms HRX server responses to fix relative URLs and render markdown.
Uses external Jinja templates from the gateway config.
"""

import re
from urllib.parse import quote
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
        missing_path = file_path
        root_entries = []
        if isinstance(content_type, str) and "application/json" in content_type:
            try:
                payload = response_details.get("json")
                if payload is None and isinstance(text, str) and text.strip():
                    import json

                    payload = json.loads(text)
                if isinstance(payload, dict):
                    missing_path = payload.get("requested_path") or missing_path
                    root_entries = payload.get("root_entries") or []
            except Exception:
                pass

        return {
            "output": _render_error_page(
                archive_cid,
                missing_path,
                text or "File not found",
                context,
                root_entries=root_entries,
            ),
            "content_type": "text/html",
            "status_code": int(status_code) if isinstance(status_code, int) else 500,
        }

    def _looks_like_directory_listing(value: str) -> bool:
        if not isinstance(value, str):
            return False
        stripped = value.strip()
        if not stripped:
            return True
        if stripped.startswith("<"):
            return False
        if stripped.startswith("{") and stripped.endswith("}"):
            return False
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if not lines:
            return True
        # Heuristic: directory listings are newline-separated path-like entries.
        for line in lines:
            if line.startswith("<") or "\0" in line:
                return False
        return True

    # If this is a directory listing, render navigation.
    # Note: directory output is typically stored as a CID and served back as text/html,
    # so we cannot rely on Content-Type.
    directory_current_path = file_path
    if _looks_like_directory_listing(text) and directory_current_path and not directory_current_path.endswith("/"):
        directory_current_path += "/"

    if _looks_like_directory_listing(text) and (
        not file_path
        or file_path.endswith("/")
        or (isinstance(file_path, str) and "." not in file_path)
    ):
        return {
            "output": _render_directory(archive_cid, directory_current_path, text, context),
            "content_type": "text/html",
        }

    # Determine file type from path
    if file_path.endswith(".md"):
        # Render markdown as HTML
        html_content = _render_markdown(text, archive_cid, file_path, context)
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
            "output": _render_text_file(text, archive_cid, file_path, context),
            "content_type": "text/html",
        }

    # Binary files - pass through
    return {
        "output": response_details.get("content", b""),
        "content_type": content_type,
    }


def _render_error_page(
    archive_cid: str,
    file_path: str,
    message: str,
    context: dict,
    *,
    root_entries: list[str] | None = None,
) -> str:
    """Render an error page."""
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")
    
    template = resolve_template("hrx_error.html")

    root_links = []
    for entry in root_entries or []:
        safe_entry = str(entry)
        href = f"/gateway/hrx/{archive_cid}/{quote(safe_entry, safe='/-_.~')}"
        icon = "📁" if safe_entry.endswith("/") else "📄"
        root_links.append({"name": safe_entry, "link": href, "icon": icon})

    return template.render(
        archive_cid=archive_cid,
        file_path=file_path,
        message=message,
        root_links=root_links,
    )


def _render_directory(archive_cid: str, current_path: str, file_list_text: str, context: dict) -> str:
    """Render a directory listing."""
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")
    
    files_list = [f.strip() for f in file_list_text.split("\n") if f.strip()]
    
    # Build breadcrumb
    breadcrumb = _build_breadcrumb(archive_cid, current_path)
    
    # Add parent directory link if not at root
    parent_link = None
    if current_path:
        parent = "/".join(current_path.rstrip("/").split("/")[:-1])
        parent_link = f"/gateway/hrx/{archive_cid}/{parent}" if parent else f"/gateway/hrx/{archive_cid}"
    
    normalized_current = (current_path or "").lstrip("/")
    if normalized_current and not normalized_current.endswith("/"):
        normalized_current += "/"

    # Build file list with icons and links
    files = []
    for file in files_list:
        name = str(file)
        joined = f"{normalized_current}{name}" if normalized_current else name
        safe_joined = quote(joined, safe="/-_.~")
        file_link = f"/gateway/hrx/{archive_cid}/{safe_joined}"
        icon = "📁" if name.endswith("/") else "📄"
        files.append({
            "name": name,
            "link": file_link,
            "icon": icon,
        })
    
    template = resolve_template("hrx_directory.html")
    return template.render(
        archive_cid=archive_cid,
        current_path=current_path,
        breadcrumb=breadcrumb,
        parent_link=parent_link,
        files=files,
    )


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


def _render_markdown(text: str, archive_cid: str, file_path: str, context: dict) -> str:
    """Render markdown as HTML with fixed links."""
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")
    
    import markdown

    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc"])
    html_content = md.convert(text)

    # Fix relative links in the rendered HTML
    html_content = _fix_relative_urls(html_content, archive_cid, file_path)

    breadcrumb = _build_breadcrumb(archive_cid, file_path)

    template = resolve_template("hrx_markdown.html")
    return template.render(
        file_path=file_path,
        breadcrumb=breadcrumb,
        html_content=html_content,
    )


def _render_text_file(text: str, archive_cid: str, file_path: str, context: dict) -> str:
    """Render a text file with syntax highlighting wrapper."""
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")
    
    breadcrumb = _build_breadcrumb(archive_cid, file_path)

    template = resolve_template("hrx_text.html")
    return template.render(
        file_path=file_path,
        breadcrumb=breadcrumb,
        text=text,
    )


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
