"""Helpers for presenting CIDs and CID-backed links consistently."""

from __future__ import annotations

from typing import Optional


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
]
