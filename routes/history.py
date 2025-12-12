"""History-related routes."""
import json
from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional

from flask import render_template, request

from analytics import get_paginated_page_views, get_history_statistics
from cid_presenter import cid_path, format_cid, render_cid_link
from cid_utils import is_strict_cid_candidate, split_cid_path
from db_access import (
    get_cids_by_paths,
    get_server_invocations_by_result_cids,
)
from models import ServerInvocation
from history_filters import parse_date_range

from . import main_bp


@main_bp.route('/history')
def history():
    """Display page view history."""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    date_range = parse_date_range(
        request.args.get('start', '', type=str),
        request.args.get('end', '', type=str),
    )

    page_views = get_paginated_page_views(
        page,
        per_page,
        start=date_range.start_at,
        end=date_range.end_at,
    )
    _attach_server_event_links(page_views)
    _attach_cid_links(page_views)
    stats = get_history_statistics(start=date_range.start_at, end=date_range.end_at)
    stats['popular_paths'] = _normalize_popular_paths(stats.get('popular_paths'))

    return render_template(
        'history.html',
        page_views=page_views,
        start_value=date_range.start_value,
        end_value=date_range.end_value,
        start_valid=date_range.start_valid,
        end_valid=date_range.end_valid,
        history_filters=date_range.filters,
        **stats,
    )


def _extract_result_cid(path: str) -> str | None:
    """Return the CID portion of a path if it looks like server output."""
    if not path:
        return None

    components = split_cid_path(path)
    if not components:
        return None

    cid_part, _ = components
    if not is_strict_cid_candidate(cid_part):
        return None

    return cid_part


def _extract_cid_components(path: Optional[str]) -> tuple[str, Optional[str]] | None:
    """Return the CID and optional extension portion of a history path."""
    return split_cid_path(path)


def _get_page_view_items(page_views: object) -> List:
    """Extract a list of page view objects from pagination or list input."""
    if page_views is None:
        return []

    items = getattr(page_views, 'items', None)
    if items is None:
        if isinstance(page_views, (list, tuple)):
            return list(page_views)
        return []

    # Ensure we always return a list instance for consistent downstream use.
    return list(items)


def _build_cid_link_details(path: Optional[str]) -> Optional[SimpleNamespace]:
    """Return CID presentation helpers for a given history path."""
    components = _extract_cid_components(path)
    if not components:
        return None

    cid_value, extension = components
    link_markup = render_cid_link(cid_value)
    if not link_markup:
        return None

    normalized_href = cid_path(cid_value, extension) if extension else cid_path(cid_value)

    fallback_path = normalized_href or f"/{cid_value}"
    visited_href = path or fallback_path
    visited_label = path or fallback_path

    return SimpleNamespace(
        value=cid_value,
        extension=extension,
        link_markup=link_markup,
        visited_href=visited_href,
        visited_label=visited_label,
        normalized_href=fallback_path,
    )


def _attach_cid_links(page_views: object) -> None:
    """Annotate page view objects with CID link helpers when applicable."""
    page_view_items = _get_page_view_items(page_views)
    if not page_view_items:
        return

    for view in page_view_items:
        cid_link = _build_cid_link_details(getattr(view, 'path', None))
        if cid_link:
            view.cid_link = cid_link


def _normalize_popular_paths(popular_paths: object) -> List[SimpleNamespace]:
    """Normalize the popular paths collection for template rendering."""
    if not popular_paths:
        return []

    normalized: List[SimpleNamespace] = []
    for entry in popular_paths:
        path_value: Optional[str] = None
        count_value: int = 0

        if isinstance(entry, (list, tuple)):
            if not entry:
                continue
            path_value = entry[0]
            if len(entry) > 1 and isinstance(entry[1], int):
                count_value = entry[1]
            elif len(entry) > 1:
                try:
                    count_value = int(entry[1])
                except (TypeError, ValueError):
                    count_value = 0
        else:
            path_value = getattr(entry, 'path', None)
            count_raw = getattr(entry, 'count', None)
            if isinstance(count_raw, int):
                count_value = count_raw
            elif count_raw is not None:
                try:
                    count_value = int(count_raw)
                except (TypeError, ValueError):
                    count_value = 0

        if path_value is None:
            continue

        cid_link = _build_cid_link_details(path_value)
        normalized.append(SimpleNamespace(
            path=path_value,
            count=count_value,
            cid_link=cid_link,
        ))

    return normalized


def _normalize_header_value(value: object) -> str | None:
    """Convert a header value into a string when possible."""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str):
                return item
        if value:
            return str(value[0])
        return None
    if value is None:
        return None
    return str(value)


def _extract_referer_from_headers(headers: object) -> str | None:
    """Return the Referer value from a headers collection."""
    if isinstance(headers, dict):
        for key, value in headers.items():
            if isinstance(key, str) and key.lower() == 'referer':
                return _normalize_header_value(value)
        return None

    if isinstance(headers, (list, tuple)):
        for item in headers:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            key, value = item[0], item[1]
            if isinstance(key, str) and key.lower() == 'referer':
                return _normalize_header_value(value)

    return None


def _load_request_referers(invocations: Iterable[ServerInvocation]) -> Dict[str, str]:
    """Load referer URLs for the provided invocations keyed by request CID."""
    request_cids = {
        invocation.request_details_cid
        for invocation in invocations
        if getattr(invocation, 'request_details_cid', None)
    }

    if not request_cids:
        return {}

    cid_paths = []
    for cid in request_cids:
        path = cid_path(cid)
        if path:
            cid_paths.append(path)
    cid_records = get_cids_by_paths(cid_paths)

    referer_by_cid: Dict[str, str] = {}
    for record in cid_records:
        raw = getattr(record, 'file_data', None)
        if not raw:
            continue

        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        referer = _extract_referer_from_headers(payload.get('headers')) if isinstance(payload, dict) else None
        if referer:
            referer_by_cid[format_cid(record.path)] = referer

    return referer_by_cid


def _attach_server_event_links(page_views: object) -> None:
    """Annotate page view objects with links to their originating server events."""
    page_view_items = _get_page_view_items(page_views)
    if not page_view_items:
        return

    result_cids = set()
    for view in page_view_items:
        cid_value = format_cid(_extract_result_cid(view.path))
        if cid_value:
            result_cids.add(cid_value)

    if not result_cids:
        return

    invocations = get_server_invocations_by_result_cids(
        result_cids,
    )

    # Prefer the most recent invocation for each result CID.
    invocation_by_result: Dict[str, ServerInvocation] = {}
    for invocation in invocations:
        if not invocation.invocation_cid:
            continue
        cid_key = format_cid(getattr(invocation, 'result_cid', None))
        if cid_key and cid_key not in invocation_by_result:
            invocation_by_result[cid_key] = invocation

    if not invocation_by_result:
        return

    referer_by_request_cid = _load_request_referers(invocation_by_result.values())

    for view in page_view_items:
        cid = format_cid(_extract_result_cid(view.path))
        if not cid:
            continue

        invocation = invocation_by_result.get(cid)
        if not invocation:
            continue

        # Attach both the invocation object and helpful links for templates.
        view.server_invocation = invocation
        invocation_cid = getattr(invocation, "cids", None)
        invocation_cid_value = getattr(invocation_cid, "invocation", None) if invocation_cid else None
        view.server_invocation_link = cid_path(invocation_cid_value or invocation.invocation_cid, 'json')

        referer = None
        request_cid = getattr(invocation, 'request_details_cid', None)
        if request_cid:
            referer = referer_by_request_cid.get(format_cid(request_cid))

        if referer:
            view.server_invocation_referer = referer


__all__ = ['history']
