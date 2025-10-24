"""Helpers for serving named alias redirects."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Generator, Iterable, Optional
from urllib.parse import urlsplit

from flask import Response, redirect, request
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import Map, Rule

from alias_definition import AliasRouteRule, collect_alias_routes
from alias_matching import matches_path
from db_access import get_user_aliases
from identity import current_user

_FLASK_PLACEHOLDER_RE = re.compile(r"<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>")


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


def _alias_routes_for_user_in_declaration_order(user_id: str) -> Generator[tuple[Any, AliasRouteRule], None, None]:
    """Yield alias routes in the order they are declared."""

    aliases = get_user_aliases(user_id)
    for alias in aliases:
        for route in collect_alias_routes(alias):
            yield alias, route


def find_matching_alias(path: str) -> Optional[AliasMatch]:
    """Return the first alias route belonging to the current user that matches the path."""

    for alias, route in _alias_routes_for_user_in_declaration_order(current_user.id):
        if matches_path(route.match_type, route.match_pattern, path, route.ignore_case):
            return AliasMatch(alias=alias, route=route)
    return None


@lru_cache(maxsize=128)
def _cached_glob_pattern(pattern: str, ignore_case: bool) -> tuple[re.Pattern[str], tuple[str, ...]]:
    """Return a compiled regex and token order for the provided glob pattern."""

    regex_parts: list[str] = []
    tokens: list[str] = []
    i = 0
    length = len(pattern)

    while i < length:
        char = pattern[i]
        i += 1
        if char == "*":
            regex_parts.append("(.*)")
            tokens.append("*")
            continue
        if char == "?":
            regex_parts.append("(.)")
            tokens.append("?")
            continue
        if char == "[":
            j = i
            if j < length and pattern[j] in "!^":
                j += 1
            if j < length and pattern[j] == "]":
                j += 1
            while j < length and pattern[j] != "]":
                j += 1
            if j >= length:
                regex_parts.append(r"\[")
            else:
                stuff = pattern[i:j].replace("\\", r"\\")
                i = j + 1
                if stuff:
                    first = stuff[0]
                    if first == "!":
                        stuff = "^" + stuff[1:]
                    elif first == "^":
                        stuff = "\\" + stuff
                regex_parts.append(f"[{stuff}]")
            continue
        regex_parts.append(re.escape(char))

    expression = "".join(regex_parts)
    flags = re.DOTALL
    if ignore_case:
        flags |= re.IGNORECASE
    compiled = re.compile(f"^{expression}$", flags)
    return compiled, tuple(tokens)


@lru_cache(maxsize=128)
def _cached_flask_map(pattern: str) -> Map:
    """Return a werkzeug routing map for the supplied Flask-style pattern."""

    return Map([Rule(pattern, endpoint="alias", methods=["GET"])])


def _substitute_star_placeholders(target: str, replacements: Iterable[str]) -> str:
    """Return the target string with '*' placeholders replaced."""

    iterator = iter(replacements)
    result: list[str] = []
    index = 0
    length = len(target)

    while index < length:
        char = target[index]
        if char == "\\":
            if index + 1 < length and target[index + 1] == "*":
                result.append("*")
                index += 2
                continue
            result.append("\\")
            index += 1
            continue
        if char == "*":
            replacement = next(iterator, "*")
            result.append(replacement)
            index += 1
            continue
        result.append(char)
        index += 1

    return "".join(result)


def _resolve_glob_target(route: AliasRouteRule, path: str) -> str:
    """Return the redirect target with glob wildcards expanded."""

    target = route.target_path or ""
    if "*" not in target:
        # No placeholders to expand.
        return _substitute_star_placeholders(target, ())

    pattern = route.match_pattern or ""
    if not pattern:
        return _substitute_star_placeholders(target, ())

    compiled, tokens = _cached_glob_pattern(pattern, route.ignore_case)
    match = compiled.match(path)
    if not match:
        return _substitute_star_placeholders(target, ())

    groups = match.groups()
    star_values = [value for token, value in zip(tokens, groups) if token == "*"]
    return _substitute_star_placeholders(target, star_values)


def _resolve_flask_target(route: AliasRouteRule, path: str) -> str:
    """Return the redirect target with Flask-style parameters inserted."""

    target = route.target_path or ""
    pattern = route.match_pattern or ""
    if not target or not pattern:
        return target

    try:
        url_map = _cached_flask_map(pattern)
        adapter = url_map.bind("", url_scheme="http")
        _, values = adapter.match(path, method="GET")
    except (NotFound, MethodNotAllowed):
        return target
    except Exception:  # pragma: no cover - defensive guard mirroring normal matching
        return target

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if not name:
            return match.group(0)
        return str(values.get(name, match.group(0)))

    return _FLASK_PLACEHOLDER_RE.sub(_replace, target)


def _resolve_target_path(route: AliasRouteRule, path: str) -> str:
    """Return the final redirect target for the matched route."""

    target = route.target_path or ""
    if not target:
        return target

    if route.match_type == "glob":
        return _resolve_glob_target(route, path)
    if route.match_type == "flask":
        return _resolve_flask_target(route, path)
    return target


def try_alias_redirect(path: str, *, alias_match: Optional[AliasMatch] = None) -> Optional[Response]:
    """Return a redirect response for an alias if one matches the path."""

    match = alias_match or find_matching_alias(path)
    if not match:
        return None

    target = _resolve_target_path(match.route, path)
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
