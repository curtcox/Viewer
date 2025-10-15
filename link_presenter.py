"""Helpers for building consistent links to aliases, servers, and other URLs."""

from __future__ import annotations

from typing import Optional

from markupsafe import Markup, escape


def _normalize_segment(value: Optional[str]) -> str:
    """Return a cleaned path segment without leading or trailing slashes."""
    if not value:
        return ""
    segment = value.strip()
    if not segment:
        return ""
    return segment.strip("/")


def _normalize_url(value: Optional[str]) -> str:
    """Return a cleaned URL or path string suitable for use in markup."""
    if not value:
        return ""
    url = value.strip()
    return url


def alias_path(name: Optional[str]) -> Optional[str]:
    """Return the URL path that serves the alias at the application root."""
    segment = _normalize_segment(name)
    if not segment:
        return None
    return f"/{segment}"


def server_path(name: Optional[str]) -> Optional[str]:
    """Return the URL path for viewing a server definition."""
    segment = _normalize_segment(name)
    if not segment:
        return None
    if segment.startswith("servers/"):
        segment = segment[len("servers/") :]
    return f"/servers/{segment}"


def _combine_base_url(base_url: Optional[str], path: Optional[str]) -> Optional[str]:
    """Combine a base URL with a relative path when both are present."""
    normalized_path = _normalize_url(path)
    if not normalized_path:
        return None
    base = _normalize_url(base_url)
    if not base:
        return normalized_path
    return f"{base.rstrip('/')}{normalized_path}"


def alias_full_url(base_url: Optional[str], name: Optional[str]) -> Optional[str]:
    """Return an absolute URL to the alias using the provided base URL."""
    return _combine_base_url(base_url, alias_path(name))


def server_full_url(base_url: Optional[str], name: Optional[str]) -> Optional[str]:
    """Return an absolute URL to the server using the provided base URL."""
    return _combine_base_url(base_url, server_path(name))


def render_url_link(
    url: Optional[str],
    *,
    label: Optional[str] = None,
    class_name: Optional[str] = None,
    code: bool = False,
) -> Markup:
    """Return markup for a clickable link with optional styling."""
    normalized_url = _normalize_url(url)
    if not normalized_url:
        return Markup("")

    text = label if label is not None else normalized_url
    class_attr = f' class="{escape(class_name)}"' if class_name else ""
    anchor = Markup(
        f'<a href="{escape(normalized_url)}"{class_attr}>{escape(text)}</a>'
    )
    if code:
        return Markup(f"<code>{anchor}</code>")
    return anchor


def render_alias_link(
    name: Optional[str],
    *,
    base_url: Optional[str] = None,
    label: Optional[str] = None,
    class_name: Optional[str] = None,
    code: bool = False,
) -> Markup:
    """Return markup for a clickable alias link."""
    path = alias_path(name)
    if not path:
        return Markup("")

    url = alias_full_url(base_url, name) if base_url else path
    if label is None:
        label = alias_full_url(base_url, name) if base_url else path
    return render_url_link(url, label=label, class_name=class_name, code=code)


def render_server_link(
    name: Optional[str],
    *,
    base_url: Optional[str] = None,
    label: Optional[str] = None,
    class_name: Optional[str] = None,
    code: bool = False,
) -> Markup:
    """Return markup for a clickable server link."""
    path = server_path(name)
    if not path:
        return Markup("")

    url = server_full_url(base_url, name) if base_url else path
    if label is None:
        label = server_full_url(base_url, name) if base_url else path
    return render_url_link(url, label=label, class_name=class_name, code=code)


__all__ = [
    "alias_full_url",
    "alias_path",
    "render_alias_link",
    "render_server_link",
    "render_url_link",
    "server_full_url",
    "server_path",
]
