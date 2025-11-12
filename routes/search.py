"""Workspace-wide search routes."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from flask import jsonify, render_template, request, url_for

from alias_definition import collect_alias_routes
from cid_presenter import cid_path, format_cid
from db_access import (
    get_user_aliases,
    get_user_secrets,
    get_user_servers,
    get_user_uploads,
    get_user_variables,
)
from identity import current_user

from . import main_bp
from .text_highlighter import TextHighlighter

# Configuration constants
_CATEGORY_CONFIG: dict[str, dict[str, Any]] = {
    "aliases": {"label": "Aliases"},
    "servers": {"label": "Servers"},
    "cids": {"label": "CIDs"},
    "variables": {"label": "Variables"},
    "secrets": {"label": "Secrets"},
}

# Search and display constants
SEARCH_CONTEXT_CHARS: int = 60
MAX_UPLOAD_HISTORY: int = 100
PREVIEW_LENGTH: int = 20

_ALIAS_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_FALSY_VALUES = frozenset({'0', 'false', 'off', 'no'})


AliasLookup = dict[str, dict[str, dict[str, str | None]]]


def _normalize_path_for_lookup(value: str | None) -> set[str]:
    """Return normalized path variations for alias lookup.

    Handles cases like:
    - With/without leading slash
    - With/without trailing slash

    Args:
        value: Path to normalize

    Returns:
        set: Normalized path variations for lookup
    """
    variants: set[str] = set()
    if value is None:
        return variants

    cleaned = value.strip()
    if not cleaned:
        return variants

    variants.add(cleaned)

    if not cleaned.startswith("/"):
        prefixed = f"/{cleaned}"
        variants.add(prefixed)
    else:
        prefixed = cleaned

    if prefixed != "/" and prefixed.endswith("/"):
        variants.add(prefixed.rstrip("/"))

    return {variant for variant in variants if variant}


def _build_alias_lookup(user_id: str, aliases: list[Any] | None = None) -> AliasLookup:
    """Build a reverse index mapping target paths to aliases.

    Creates a lookup table where keys are normalized path variants and values
    are dictionaries of aliases that reference those paths. This enables
    efficient "what aliases point to this path?" queries.

    Args:
        user_id: User ID to filter aliases
        aliases: Optional pre-fetched alias list (avoids DB query)

    Returns:
        Nested dict: {path_variant: {alias_name: alias_info}}

    Example:
        {
            "/api/endpoint": {
                "my_alias": {"name": "my_alias", "url": "/alias/my_alias", ...}
            }
        }
    """
    lookup: AliasLookup = {}
    source = aliases if aliases is not None else get_user_aliases(user_id)

    for alias in source:
        name = getattr(alias, "name", "") or ""
        if not name:
            continue

        routes = collect_alias_routes(alias)
        if not routes:
            continue

        entry = {
            "name": name,
            "url": url_for("main.view_alias", alias_name=name),
            "enabled": bool(getattr(alias, "enabled", True)),
        }

        for route in routes:
            target_path = route.target_path or ""
            if not target_path:
                continue

            for key in _normalize_path_for_lookup(target_path):
                bucket = lookup.setdefault(key, {})
                bucket[name] = entry

    return lookup


def _alias_matches_for(target_path: str | None, lookup: AliasLookup | None) -> list[dict[str, str | None]]:
    """Return aliases referencing the provided target path."""

    if not lookup or target_path is None:
        return []

    matches: dict[str, dict[str, str | None]] = {}
    for key in _normalize_path_for_lookup(target_path):
        bucket = lookup.get(key)
        if not bucket:
            continue
        matches.update(bucket)

    if not matches:
        return []

    return sorted(matches.values(), key=lambda entry: (entry.get("name") or "").lower())


def _alias_form_url(target_path: str | None, name_suggestion: str | None = None) -> str | None:
    """Return the alias creation URL with helpful defaults when possible."""

    if not target_path:
        return None

    params: dict[str, str] = {"target_path": target_path}

    if name_suggestion and _ALIAS_NAME_PATTERN.fullmatch(name_suggestion):
        params["name"] = name_suggestion

    return url_for("main.new_alias", **params)


def _parse_enabled(value: str | None) -> bool:
    """Return True when a category should be included in search.

    Treats None and empty strings as True (enabled by default).
    Recognizes: '0', 'false', 'off', 'no' as False.

    Args:
        value: String value to parse

    Returns:
        bool: True if category should be included
    """
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in _FALSY_VALUES


def _alias_results(
    user_id: str,
    query_lower: str,
    alias_lookup: AliasLookup | None = None,
    aliases: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    source = aliases if aliases is not None else get_user_aliases(user_id)

    for alias in source:
        name_text = getattr(alias, "name", "") or ""
        routes = collect_alias_routes(alias)
        if not routes:
            continue

        target_paths = [route.target_path or "" for route in routes if route.target_path]
        match_patterns = [route.match_pattern or "" for route in routes if route.match_pattern]

        if not (
            TextHighlighter.has_match(name_text, query_lower)
            or any(TextHighlighter.has_match(path, query_lower) for path in target_paths)
            or any(TextHighlighter.has_match(pattern, query_lower) for pattern in match_patterns)
        ):
            continue

        details: list[dict[str, str]] = []
        for label, values in (
            ("Target Path", target_paths),
            ("Match Pattern", match_patterns),
        ):
            for value in values:
                highlighted = TextHighlighter.highlight_full(value, query_lower)
                if "<mark>" in highlighted:
                    details.append({"label": label, "value": highlighted})
                    break

        primary_route = routes[0]
        canonical_path = (primary_route.target_path or "").strip() or None
        results.append(
            {
                "id": getattr(alias, "id", None),
                "name": name_text,
                "name_highlighted": TextHighlighter.highlight_full(name_text, query_lower),
                "url": url_for("main.view_alias", alias_name=name_text) if name_text else None,
                "details": details,
                "aliases": _alias_matches_for(canonical_path, alias_lookup),
                "alias_form_url": _alias_form_url(canonical_path),
                "enabled": bool(getattr(alias, "enabled", True)),
            }
        )
    return results


def _server_results(
    user_id: str,
    query_lower: str,
    alias_lookup: AliasLookup | None = None,
    _unused_aliases: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for server in get_user_servers(user_id):
        name_text = getattr(server, "name", "") or ""
        definition = getattr(server, "definition", "") or ""

        if not (TextHighlighter.has_match(name_text, query_lower) or TextHighlighter.has_match(definition, query_lower)):
            continue

        details: list[dict[str, str]] = []
        snippet = TextHighlighter.highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_server", server_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(server, "id", None),
                "name": name_text,
                "name_highlighted": TextHighlighter.highlight_full(name_text, query_lower),
                "url": canonical_path,
                "details": details,
                "aliases": _alias_matches_for(canonical_path, alias_lookup),
                "alias_form_url": _alias_form_url(canonical_path, name_text),
                "enabled": bool(getattr(server, "enabled", True)),
            }
        )
    return results


def _variable_results(
    user_id: str,
    query_lower: str,
    alias_lookup: AliasLookup | None = None,
    _unused_aliases: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for variable in get_user_variables(user_id):
        name_text = getattr(variable, "name", "") or ""
        definition = getattr(variable, "definition", "") or ""

        if not (TextHighlighter.has_match(name_text, query_lower) or TextHighlighter.has_match(definition, query_lower)):
            continue

        details: list[dict[str, str]] = []
        snippet = TextHighlighter.highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_variable", variable_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(variable, "id", None),
                "name": name_text,
                "name_highlighted": TextHighlighter.highlight_full(name_text, query_lower),
                "url": canonical_path,
                "details": details,
                "aliases": _alias_matches_for(canonical_path, alias_lookup),
                "alias_form_url": _alias_form_url(canonical_path, name_text),
                "enabled": bool(getattr(variable, "enabled", True)),
            }
        )
    return results


def _secret_results(
    user_id: str,
    query_lower: str,
    alias_lookup: AliasLookup | None = None,
    _unused_aliases: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for secret in get_user_secrets(user_id):
        name_text = getattr(secret, "name", "") or ""
        definition = getattr(secret, "definition", "") or ""

        if not (TextHighlighter.has_match(name_text, query_lower) or TextHighlighter.has_match(definition, query_lower)):
            continue

        details: list[dict[str, str]] = []
        snippet = TextHighlighter.highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_secret", secret_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(secret, "id", None),
                "name": name_text,
                "name_highlighted": TextHighlighter.highlight_full(name_text, query_lower),
                "url": canonical_path,
                "details": details,
                "aliases": _alias_matches_for(canonical_path, alias_lookup),
                "alias_form_url": _alias_form_url(canonical_path, name_text),
                "enabled": bool(getattr(secret, "enabled", True)),
            }
        )
    return results


def _cid_results(
    user_id: str,
    query_lower: str,
    alias_lookup: AliasLookup | None = None,
    _unused_aliases: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def created_at_value(record: Any) -> datetime:
        value = getattr(record, "created_at", None)
        if value is None:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    uploads = sorted(
        get_user_uploads(user_id),
        key=created_at_value,
        reverse=True,
    )[:MAX_UPLOAD_HISTORY]

    for cid_record in uploads:
        path = getattr(cid_record, "path", "") or ""
        cid_value = format_cid(path)
        display_name = path or (f"/{cid_value}" if cid_value else "")

        file_data = getattr(cid_record, "file_data", b"") or b""
        try:
            content_text = file_data.decode("utf-8", errors="replace")
        except UnicodeDecodeError:  # pragma: no cover - errors="replace" prevents this
            content_text = ""

        if not (
            TextHighlighter.has_match(display_name, query_lower)
            or TextHighlighter.has_match(cid_value, query_lower)
            or TextHighlighter.has_match(content_text, query_lower)
        ):
            continue

        details: list[dict[str, str]] = []
        snippet = TextHighlighter.highlight_snippet(content_text, query_lower)
        if snippet:
            details.append({"label": "Content", "value": snippet})

        canonical_path = cid_path(cid_value) if cid_value else (display_name or None)
        alias_name_suggestion = cid_value if cid_value and _ALIAS_NAME_PATTERN.fullmatch(cid_value) else None

        results.append(
            {
                "id": getattr(cid_record, "id", None),
                "name": display_name,
                "name_highlighted": TextHighlighter.highlight_full(display_name, query_lower),
                "url": canonical_path,
                "details": details,
                "aliases": _alias_matches_for(canonical_path, alias_lookup),
                "alias_form_url": _alias_form_url(canonical_path, alias_name_suggestion),
            }
        )
    return results


_COLLECTORS = {
    "aliases": _alias_results,
    "servers": _server_results,
    "variables": _variable_results,
    "secrets": _secret_results,
    "cids": _cid_results,
}


@main_bp.route("/search")
def search_page():
    """Render the workspace search page."""

    return render_template("search.html", title="Search")


def _extract_search_query() -> tuple[str, str]:
    """Extract and normalize the search query from request parameters.

    Returns:
        tuple: (original_query, lowercase_query)
    """
    query = (request.args.get("q") or "").strip()
    query_lower = query.lower()
    return query, query_lower


def _parse_search_filters() -> dict[str, bool]:
    """Parse category filter parameters from the request.

    Returns:
        dict: Mapping of category keys to their enabled status
    """
    return {
        key: _parse_enabled(request.args.get(key)) for key in _CATEGORY_CONFIG
    }


def _empty_search_response(applied_filters: dict[str, bool]) -> dict[str, Any]:
    """Create an empty search response with no results.

    Args:
        applied_filters: Current filter configuration

    Returns:
        dict: Empty search response structure
    """
    response_categories: dict[str, dict[str, Any]] = {}
    for key, config in _CATEGORY_CONFIG.items():
        response_categories[key] = {
            "label": config["label"],
            "count": 0,
            "items": [],
        }
    return {
        "query": "",
        "total_count": 0,
        "categories": response_categories,
        "applied_filters": applied_filters,
    }


def _execute_search(
    user_id: str,
    query_lower: str,
    applied_filters: dict[str, bool],
    alias_lookup: AliasLookup,
    alias_records: list[Any]
) -> tuple[dict[str, dict[str, Any]], int]:
    """Execute search across all enabled categories.

    Args:
        user_id: Current user ID
        query_lower: Lowercase search query
        applied_filters: Category filter configuration
        alias_lookup: Precomputed alias lookup table
        alias_records: List of user aliases

    Returns:
        tuple: (response_categories, total_count)
    """
    response_categories: dict[str, dict[str, Any]] = {}
    total_count = 0

    for key, config in _CATEGORY_CONFIG.items():
        include = applied_filters.get(key, True)
        if include:
            collector = _COLLECTORS.get(key)
            if collector:
                items = collector(user_id, query_lower, alias_lookup, alias_records)
            else:
                items = []
        else:
            items = []

        count = len(items)
        if include:
            total_count += count

        response_categories[key] = {
            "label": config["label"],
            "count": count,
            "items": items,
        }

    return response_categories, total_count


@main_bp.route("/search/results")
def search_results():
    """Return JSON search results for the requested query and filters."""
    query, query_lower = _extract_search_query()
    applied_filters = _parse_search_filters()

    if not query_lower:
        return jsonify(_empty_search_response(applied_filters))

    user_id = current_user.id
    alias_records = get_user_aliases(user_id)
    alias_lookup = _build_alias_lookup(user_id, alias_records)

    response_categories, total_count = _execute_search(
        user_id, query_lower, applied_filters, alias_lookup, alias_records
    )

    return jsonify(
        {
            "query": query,
            "total_count": total_count,
            "categories": response_categories,
            "applied_filters": applied_filters,
        }
    )


__all__ = ["search_page", "search_results"]
