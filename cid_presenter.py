"""Helpers for presenting CIDs and CID-backed links consistently."""

from __future__ import annotations

from typing import Optional

from markupsafe import Markup, escape


def _normalize_value(value: Optional[str]) -> str:
    """Return a normalized CID value without leading slashes or surrounding whitespace."""
    if value is None:
        return ""
    stripped = value.strip()
    if stripped.startswith("/"):
        stripped = stripped.lstrip("/")
    return stripped


def format_cid(value: Optional[str]) -> str:
    """Return a canonical string representation of a CID for display."""
    return _normalize_value(value)


def format_cid_short(value: Optional[str], length: int = 6) -> Optional[str]:
    """Return a shortened CID label suitable for compact displays."""
    normalized = _normalize_value(value)
    if not normalized:
        return None
    if len(normalized) <= length:
        return normalized
    return f"{normalized[:length]}..."


def _cid_label(normalized: str) -> str:
    """Return the standardized label text for a CID link."""
    if not normalized:
        return ""
    prefix = normalized[:9]
    return f"#{prefix}..."


def render_cid_link(value: Optional[str]) -> Markup:
    """Return markup for displaying a CID with navigation and quick actions."""
    normalized = _normalize_value(value)
    if not normalized:
        return Markup("")

    base_path = cid_path(normalized) or ""
    text_path = cid_path(normalized, "txt") or ""
    markdown_path = cid_path(normalized, "md") or ""
    edit_path = f"/edit/{normalized}"
    meta_path = f"/meta/{normalized}"

    label = _cid_label(normalized)

    return Markup(
        """
<span class="cid-display dropdown">
    <a class="cid-link" href="{base_href}" title="{title}">{label}</a>
    <button
        type="button"
        class="btn btn-sm btn-outline-secondary cid-menu-btn dropdown-toggle"
        data-bs-toggle="dropdown"
        data-bs-boundary="viewport"
        data-bs-offset="0,8"
        aria-expanded="false"
        aria-haspopup="true"
        aria-label="More options for CID {title}"
    >
        <i class="fas fa-ellipsis-vertical"></i>
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        <li><a class="dropdown-item" href="{text_href}"><i class="fas fa-file-alt text-muted me-2"></i>View as text</a></li>
        <li><a class="dropdown-item" href="{markdown_href}"><i class="fas fa-file-code text-muted me-2"></i>View as markdown</a></li>
        <li><a class="dropdown-item" href="{edit_href}"><i class="fas fa-edit text-muted me-2"></i>Edit</a></li>
        <li><a class="dropdown-item" href="{meta_href}"><i class="fas fa-circle-info text-muted me-2"></i>View metadata</a></li>
    </ul>
</span>
""".format(
            base_href=escape(base_path),
            title=escape(normalized),
            label=escape(label),
            text_href=escape(text_path),
            markdown_href=escape(markdown_path),
            edit_href=escape(edit_path),
            meta_href=escape(meta_path),
        )
    )


def cid_path(value: Optional[str], extension: Optional[str] = None) -> Optional[str]:
    """Return a relative path to CID content, optionally appending an extension."""
    normalized = _normalize_value(value)
    if not normalized:
        return None

    suffix = ""
    if extension:
        ext = extension.strip()
        if ext:
            suffix = f".{ext.lstrip('.')}"

    return f"/{normalized}{suffix}"


def cid_full_url(base_url: str, value: Optional[str], extension: Optional[str] = None) -> Optional[str]:
    """Return an absolute URL pointing at CID content using the provided base URL."""
    path = cid_path(value, extension)
    if not path:
        return None
    base = (base_url or "").rstrip("/")
    return f"{base}{path}"


__all__ = [
    "cid_full_url",
    "cid_path",
    "format_cid",
    "format_cid_short",
    "render_cid_link",
]
