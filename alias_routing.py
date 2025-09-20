"""Helpers for serving named alias redirects."""
from __future__ import annotations

from typing import Iterable, Optional

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
    if not target:
        return None

    query = request.query_string.decode("utf-8")
    if query:
        separator = "&" if "?" in target else "?"
        target = f"{target}{separator}{query}"

    return redirect(target)


__all__ = ["is_potential_alias_path", "try_alias_redirect"]
