"""Workspace-wide search routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import jsonify, render_template, request, url_for
from markupsafe import escape

from cid_presenter import cid_path, format_cid
from db_access import (
    get_user_aliases,
    get_user_servers,
    get_user_secrets,
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


def _alias_results(user_id: str, query_lower: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for alias in get_user_aliases(user_id):
        name_text = getattr(alias, "name", "") or ""
        target_path = getattr(alias, "target_path", "") or ""
        match_pattern = getattr(alias, "match_pattern", "") or ""

        if not (
            _has_match(name_text, query_lower)
            or _has_match(target_path, query_lower)
            or _has_match(match_pattern, query_lower)
        ):
            continue

        details: List[Dict[str, str]] = []
        for label, value in (
            ("Target Path", target_path),
            ("Match Pattern", match_pattern),
        ):
            highlighted = _highlight_full(value, query_lower)
            if "<mark>" in highlighted:
                details.append({"label": label, "value": highlighted})

        results.append(
            {
                "id": getattr(alias, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
                "url": url_for("main.view_alias", alias_name=name_text) if name_text else None,
                "details": details,
            }
        )
    return results


def _server_results(user_id: str, query_lower: str) -> List[Dict[str, Any]]:
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

        results.append(
            {
                "id": getattr(server, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
                "url": url_for("main.view_server", server_name=name_text) if name_text else None,
                "details": details,
            }
        )
    return results


def _variable_results(user_id: str, query_lower: str) -> List[Dict[str, Any]]:
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

        results.append(
            {
                "id": getattr(variable, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
                "url": url_for("main.view_variable", variable_name=name_text) if name_text else None,
                "details": details,
            }
        )
    return results


def _secret_results(user_id: str, query_lower: str) -> List[Dict[str, Any]]:
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

        results.append(
            {
                "id": getattr(secret, "id", None),
                "name": name_text,
                "name_highlighted": _highlight_full(name_text, query_lower),
                "url": url_for("main.view_secret", secret_name=name_text) if name_text else None,
                "details": details,
            }
        )
    return results


def _cid_results(user_id: str, query_lower: str) -> List[Dict[str, Any]]:
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
        except Exception:  # pragma: no cover - extremely unlikely due to errors="replace"
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

        results.append(
            {
                "id": getattr(cid_record, "id", None),
                "name": display_name,
                "name_highlighted": _highlight_full(display_name, query_lower),
                "url": cid_path(cid_value) if cid_value else display_name,
                "details": details,
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
    total_count = 0

    for key, config in _CATEGORY_CONFIG.items():
        include = applied_filters.get(key, True)
        if include:
            collector = _COLLECTORS.get(key)
            items = collector(user_id, query_lower) if collector else []
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
