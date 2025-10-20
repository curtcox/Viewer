"""Helpers for serving named alias redirects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from urllib.parse import urlsplit

from flask import redirect, request

from identity import current_user

from alias_definition import AliasRouteRule, collect_alias_routes
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


@dataclass(frozen=True)
class AliasMatch:
    """Match result tying a request path to an alias routing rule."""

    alias: object
    route: AliasRouteRule


def _sorted_alias_routes_for_user(user_id: str):
    aliases = get_user_aliases(user_id)
    decorated = []
    for alias in aliases:
        for route in collect_alias_routes(alias):
            decorated.append((alias_sort_key(route.match_type, route.match_pattern), alias, route))
    decorated.sort(key=lambda item: item[0])
    for _, alias, route in decorated:
        yield alias, route


def find_matching_alias(path: str) -> Optional[AliasMatch]:
    """Return the first alias route belonging to the current user that matches the path."""

    for alias, route in _sorted_alias_routes_for_user(current_user.id):
        if matches_path(route.match_type, route.match_pattern, path, route.ignore_case):
            return AliasMatch(alias=alias, route=route)
    return None


def try_alias_redirect(path: str, *, alias_match: Optional[AliasMatch] = None):
    """Return a redirect response for an alias if one matches the path."""

    match = alias_match or find_matching_alias(path)
    if not match:
        return None

    target = match.route.target_path
    if not target or not _is_relative_target(target):
        return None

    query = request.query_string.decode("utf-8")
    if query:
        target = _append_query_string(target, query)

    status_code = 302
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        status_code = 307
    return redirect(target, code=status_code)


__all__ = ["AliasMatch", "find_matching_alias", "is_potential_alias_path", "try_alias_redirect"]
