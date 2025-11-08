"""Workspace-wide search routes."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import jsonify, render_template, request, url_for
from markupsafe import escape

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

_CATEGORY_CONFIG: Dict[str, Dict[str, Any]] = {
    "aliases": {"label": "Aliases"},
    "servers": {"label": "Servers"},
    "cids": {"label": "CIDs"},
    "variables": {"label": "Variables"},
    "secrets": {"label": "Secrets"},
}


_ALIAS_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


AliasLookup = Dict[str, Dict[str, Dict[str, Optional[str]]]]


def _lookup_key_variants(value: Optional[str]) -> set[str]:
    """Return candidate lookup keys for the supplied path."""

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


def _build_alias_lookup(user_id: str, aliases: Optional[List[Any]] = None) -> AliasLookup:
    """Return a mapping of target paths to aliases referencing them."""

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

            for key in _lookup_key_variants(target_path):
                bucket = lookup.setdefault(key, {})
                bucket[name] = entry

    return lookup


def _alias_matches_for(target_path: Optional[str], lookup: Optional[AliasLookup]) -> List[Dict[str, Optional[str]]]:
    """Return aliases referencing the provided target path."""

    if not lookup or target_path is None:
        return []

    matches: Dict[str, Dict[str, Optional[str]]] = {}
    for key in _lookup_key_variants(target_path):
        bucket = lookup.get(key)
        if not bucket:
            continue
        matches.update(bucket)

    if not matches:
        return []

    return sorted(matches.values(), key=lambda entry: (entry.get("name") or "").lower())


def _alias_form_url(target_path: Optional[str], name_suggestion: Optional[str] = None) -> Optional[str]:
    """Return the alias creation URL with helpful defaults when possible."""

    if not target_path:
        return None

    params: Dict[str, str] = {"target_path": target_path}

    if name_suggestion and _ALIAS_NAME_PATTERN.fullmatch(name_suggestion):
        params["name"] = name_suggestion

    return url_for("main.new_alias", **params)


def _parse_enabled(value: str | None) -> bool:
    """Return True when a category should be included in the search."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "off", "no"}


def _has_match(text: str | None, query_lower: str) -> bool:
    """Return True when the search term appears in the supplied text."""

    if not text or not query_lower:
        return False
    return query_lower in text.lower()


def _highlight_full(text: str | None, query_lower: str) -> str:
    """Return the supplied text with all matches wrapped in <mark> tags."""

    if not text:
        return ""
    if not query_lower:
        return str(escape(text))

    lower_text = text.lower()
    query_length = len(query_lower)
    if query_length == 0:
        return str(escape(text))

    result_parts: List[str] = []
    cursor = 0

    while True:
        match_index = lower_text.find(query_lower, cursor)
        if match_index == -1:
            remaining = text[cursor:]
            if remaining:
                result_parts.append(str(escape(remaining)))
            break

        if match_index > cursor:
            result_parts.append(str(escape(text[cursor:match_index])))

        matched_text = text[match_index: match_index + query_length]
        result_parts.append(f"<mark>{escape(matched_text)}</mark>")
        cursor = match_index + query_length

    return "".join(result_parts)


def _highlight_snippet(text: str | None, query_lower: str, *, context: int = 60) -> str:
    """Return a snippet of text around the first match with highlighting."""

    if not text or not query_lower:
        return ""

    lower_text = text.lower()
    match_index = lower_text.find(query_lower)
    if match_index == -1:
        return ""

    query_length = len(query_lower)
    start = max(match_index - context, 0)
    end = min(match_index + query_length + context, len(text))

    snippet = text[start:end]
    highlighted = _highlight_full(snippet, query_lower)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{highlighted}{suffix}"


def _alias_results(
    user_id: str,
    query_lower: str,
    alias_lookup: Optional[AliasLookup] = None,
    aliases: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    source = aliases if aliases is not None else get_user_aliases(user_id)

    for alias in source:
        name_text = getattr(alias, "name", "") or ""
        routes = collect_alias_routes(alias)
        if not routes:
            continue

        target_paths = [route.target_path or "" for route in routes if route.target_path]
        match_patterns = [route.match_pattern or "" for route in routes if route.match_pattern]

        if not (
            _has_match(name_text, query_lower)
            or any(_has_match(path, query_lower) for path in target_paths)
            or any(_has_match(pattern, query_lower) for pattern in match_patterns)
        ):
            continue

        details: List[Dict[str, str]] = []
        for label, values in (
            ("Target Path", target_paths),
            ("Match Pattern", match_patterns),
        ):
            for value in values:
                highlighted = _highlight_full(value, query_lower)
                if "<mark>" in highlighted:
                    details.append({"label": label, "value": highlighted})
                    break

        primary_route = routes[0]
        canonical_path = (primary_route.target_path or "").strip() or None
        results.append(
            {
                "id": getattr(alias, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
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
    alias_lookup: Optional[AliasLookup] = None,
    _unused_aliases: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for server in get_user_servers(user_id):
        name_text = getattr(server, "name", "") or ""
        definition = getattr(server, "definition", "") or ""

        if not (_has_match(name_text, query_lower) or _has_match(definition, query_lower)):
            continue

        details: List[Dict[str, str]] = []
        snippet = _highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_server", server_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(server, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
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
    alias_lookup: Optional[AliasLookup] = None,
    _unused_aliases: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for variable in get_user_variables(user_id):
        name_text = getattr(variable, "name", "") or ""
        definition = getattr(variable, "definition", "") or ""

        if not (_has_match(name_text, query_lower) or _has_match(definition, query_lower)):
            continue

        details: List[Dict[str, str]] = []
        snippet = _highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_variable", variable_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(variable, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
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
    alias_lookup: Optional[AliasLookup] = None,
    _unused_aliases: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for secret in get_user_secrets(user_id):
        name_text = getattr(secret, "name", "") or ""
        definition = getattr(secret, "definition", "") or ""

        if not (_has_match(name_text, query_lower) or _has_match(definition, query_lower)):
            continue

        details: List[Dict[str, str]] = []
        snippet = _highlight_snippet(definition, query_lower)
        if snippet:
            details.append({"label": "Definition", "value": snippet})

        canonical_path = url_for("main.view_secret", secret_name=name_text) if name_text else None

        results.append(
            {
                "id": getattr(secret, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
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
    alias_lookup: Optional[AliasLookup] = None,
    _unused_aliases: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

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
    )[:100]

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
            _has_match(display_name, query_lower)
            or _has_match(cid_value, query_lower)
            or _has_match(content_text, query_lower)
        ):
            continue

        details: List[Dict[str, str]] = []
        snippet = _highlight_snippet(content_text, query_lower)
        if snippet:
            details.append({"label": "Content", "value": snippet})

        canonical_path = cid_path(cid_value) if cid_value else (display_name or None)
        alias_name_suggestion = cid_value if cid_value and _ALIAS_NAME_PATTERN.fullmatch(cid_value) else None

        results.append(
            {
                "id": getattr(cid_record, "id", None),
                "name": display_name,
                "name_highlighted": _highlight_full(display_name, query_lower),
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


@main_bp.route("/search/results")
def search_results():
    """Return JSON search results for the requested query and filters."""

    query = (request.args.get("q") or "").strip()
    query_lower = query.lower()

    applied_filters = {
        key: _parse_enabled(request.args.get(key)) for key in _CATEGORY_CONFIG
    }

    response_categories: Dict[str, Dict[str, Any]] = {}

    if not query_lower:
        for key, config in _CATEGORY_CONFIG.items():
            response_categories[key] = {
                "label": config["label"],
                "count": 0,
                "items": [],
            }
        return jsonify(
            {
                "query": query,
                "total_count": 0,
                "categories": response_categories,
                "applied_filters": applied_filters,
            }
        )

    user_id = current_user.id
    alias_records = get_user_aliases(user_id)
    alias_lookup = _build_alias_lookup(user_id, alias_records)
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

    return jsonify(
        {
            "query": query,
            "total_count": total_count,
            "categories": response_categories,
            "applied_filters": applied_filters,
        }
    )


__all__ = ["search_page", "search_results"]
