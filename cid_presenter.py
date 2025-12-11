"""Helpers for presenting CIDs and CID-backed links consistently."""

from __future__ import annotations

import re
from typing import Optional, Union

from markupsafe import Markup, escape

from cid import CID

_CID_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,}$")

def _normalize_value(value: Optional[Union[str, CID]]) -> str:
    """Return a normalized CID value without leading slashes or surrounding whitespace."""
    if value is None:
        return ""
    if isinstance(value, CID):
        raw = value.value
    else:
        raw = value
    stripped = raw.strip()
    if stripped.startswith("/"):
        stripped = stripped.lstrip("/")
    return stripped

def format_cid(value: Optional[Union[str, CID]]) -> str:
    """Return a canonical string representation of a CID for display."""
    return _normalize_value(value)


def extract_cid_from_path(value: Optional[str]) -> Optional[str]:
    """Return the CID component from a likely CID path."""

    if value is None:
        return None

    slug = value.strip()
    if not slug:
        return None

    slug = slug.split("?", 1)[0]
    slug = slug.split("#", 1)[0]
    if slug.startswith("/"):
        slug = slug[1:]

    if not slug or "/" in slug:
        return None

    cid_part = slug
    if "." in cid_part:
        cid_part = cid_part.split(".", 1)[0]

    if not _CID_REFERENCE_PATTERN.fullmatch(cid_part):
        return None

    return cid_part or None


def is_probable_cid_path(value: Optional[str]) -> bool:
    """Return True when the supplied path appears to reference a CID."""

    return extract_cid_from_path(value) is not None

def format_cid_short(value: Optional[Union[str, CID]], length: int = 6) -> Optional[str]:
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

def render_cid_link(value: Optional[Union[str, CID]]) -> Markup:
    """Return markup for displaying a CID with navigation and quick actions."""
    normalized = _normalize_value(value)
    if not normalized:
        return Markup("")

    raw_path = cid_path(normalized) or ""
    text_path = cid_path(normalized, "txt") or ""
    markdown_path = cid_path(normalized, "md") or ""
    html_path = cid_path(normalized, "html") or ""
    json_path = cid_path(normalized, "json") or ""
    png_path = cid_path(normalized, "png") or ""
    jpg_path = cid_path(normalized, "jpg") or ""
    qr_path = cid_path(normalized, "qr") or ""
    edit_path = f"/edit/{normalized}"
    meta_path = f"/meta/{normalized}"
    primary_path = text_path or raw_path
    copy_path = primary_path

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
        <li><a class="dropdown-item" href="{html_href}"><i class="fas fa-file-code text-muted me-2"></i>View as HTML</a></li>
        <li><a class="dropdown-item" href="{json_href}"><i class="fas fa-code text-muted me-2"></i>View as JSON</a></li>
        <li><a class="dropdown-item" href="{png_href}"><i class="fas fa-file-image text-muted me-2"></i>View as PNG</a></li>
        <li><a class="dropdown-item" href="{jpg_href}"><i class="fas fa-file-image text-muted me-2"></i>View as JPG</a></li>
        <li><a class="dropdown-item" href="{qr_href}"><i class="fas fa-qrcode text-muted me-2"></i>View as QR</a></li>
        <li><a class="dropdown-item" href="{edit_href}"><i class="fas fa-edit text-muted me-2"></i>Edit</a></li>
        <li><a class="dropdown-item" href="{meta_href}"><i class="fas fa-circle-info text-muted me-2"></i>View metadata</a></li>
        <li><hr class="dropdown-divider"></li>
        <li>
            <button type="button" class="dropdown-item cid-copy-action" data-copy-path="{copy_path}">
                <i class="fas fa-copy text-muted me-2"></i>Copy link
            </button>
        </li>
    </ul>
</span>
""".format(
            base_href=escape(primary_path or ""),
            title=escape(normalized),
            label=escape(label),
            copy_path=escape(copy_path or ""),
            text_href=escape(text_path),
            markdown_href=escape(markdown_path),
            html_href=escape(html_path),
            json_href=escape(json_path),
            png_href=escape(png_path),
            jpg_href=escape(jpg_path),
            qr_href=escape(qr_path),
            edit_href=escape(edit_path),
            meta_href=escape(meta_path),
        )
    )

def cid_path(value: Optional[Union[str, CID]], extension: Optional[str] = None) -> Optional[str]:
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

def cid_full_url(base_url: str, value: Optional[Union[str, CID]], extension: Optional[str] = None) -> Optional[str]:
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
    "extract_cid_from_path",
    "is_probable_cid_path",
    "render_cid_link",
]
