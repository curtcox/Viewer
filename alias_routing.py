"""Helpers for serving named alias redirects."""
from __future__ import annotations

from typing import Iterable, Optional

from urllib.parse import urlsplit

from flask import redirect, request
from flask_login import current_user

from db_access import get_alias_by_name


def _extract_alias_name(path: str) -> Optional[str]:
    """Return the first path segment if present."""
    if not path or not path.startswith("/"):
        return None

    remainder = path[1:]
    if not remainder:
        return None

    return remainder.split("/", 1)[0]


def is_potential_alias_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True when the request path could map to an alias."""
    alias_name = _extract_alias_name(path)
    if not alias_name:
        return False

    if f"/{alias_name}" in existing_routes:
        return False

    return True


def _is_relative_target(target: str) -> bool:
    """Return True when the alias target stays on this server."""
    if not target:
        return False

    if target.startswith("//"):
        return False

    parsed = urlsplit(target)
    return not parsed.scheme and not parsed.netloc


def _append_query_string(target: str, query: str) -> str:
    """Attach the provided query string while respecting fragments."""
    if not query:
        return target

    base, has_fragment, fragment = target.partition("#")

    if "?" in base:
        separator = "" if base.endswith("?") else "&"
    else:
        separator = "?"

    combined_base = f"{base}{separator}{query}" if base else f"?{query}"
    if has_fragment:
        return f"{combined_base}#{fragment}"
    return combined_base


def try_alias_redirect(path: str):
    """Return a redirect response for an alias if one matches the path."""
    if not getattr(current_user, "is_authenticated", False):
        return None

    alias_name = _extract_alias_name(path)
    if not alias_name:
        return None

    alias = get_alias_by_name(current_user.id, alias_name)
    if not alias:
        return None

    target = getattr(alias, "target_path", None)
    if not target or not _is_relative_target(target):
        return None

    query = request.query_string.decode("utf-8")
    if query:
        target = _append_query_string(target, query)

    return redirect(target)


__all__ = ["is_potential_alias_path", "try_alias_redirect"]
