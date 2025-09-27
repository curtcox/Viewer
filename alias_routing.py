"""Helpers for serving named alias redirects."""
from __future__ import annotations

from typing import Iterable, Optional, Tuple

from urllib.parse import urlsplit

from flask import redirect, request
from flask_login import current_user

from alias_matching import alias_sort_key, matches_path
from db_access import get_user_aliases


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


def _effective_pattern_and_type(alias) -> Tuple[str, str]:
    match_type = getattr(alias, "match_type", None) or "literal"
    if hasattr(alias, "get_effective_pattern"):
        pattern = alias.get_effective_pattern()
    else:
        pattern = getattr(alias, "match_pattern", None)
        if not pattern:
            name = getattr(alias, "name", "") or ""
            pattern = f"/{name}" if name else "/"
    return pattern, match_type


def _sorted_aliases_for_user(user_id: str):
    aliases = get_user_aliases(user_id)
    decorated = []
    for alias in aliases:
        pattern, match_type = _effective_pattern_and_type(alias)
        decorated.append((alias_sort_key(match_type, pattern), alias, pattern, match_type))
    decorated.sort(key=lambda item: item[0])
    for _, alias, pattern, match_type in decorated:
        yield alias, match_type, pattern


def find_matching_alias(path: str):
    """Return the first alias belonging to the current user that matches the path."""

    if not getattr(current_user, "is_authenticated", False):
        return None

    for alias, match_type, pattern in _sorted_aliases_for_user(current_user.id):
        ignore_case = bool(getattr(alias, "ignore_case", False))
        if matches_path(match_type, pattern, path, ignore_case):
            return alias
    return None


def try_alias_redirect(path: str):
    """Return a redirect response for an alias if one matches the path."""

    alias = find_matching_alias(path)
    if not alias:
        return None

    target = getattr(alias, "target_path", None)
    if not target or not _is_relative_target(target):
        return None

    query = request.query_string.decode("utf-8")
    if query:
        target = _append_query_string(target, query)

    return redirect(target)


__all__ = ["find_matching_alias", "is_potential_alias_path", "try_alias_redirect"]
