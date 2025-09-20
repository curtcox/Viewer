"""History-related routes."""
import json
import re
from typing import Dict, Iterable, List

from flask import render_template, request
from flask_login import current_user

from auth_providers import require_login
from analytics import get_paginated_page_views, get_user_history_statistics
from models import CID, ServerInvocation

from . import main_bp


@main_bp.route('/history')
@require_login
def history():
    """Display user's page view history."""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    page_views = get_paginated_page_views(current_user.id, page, per_page)
    _attach_server_event_links(page_views)
    stats = get_user_history_statistics(current_user.id)

    return render_template('history.html', page_views=page_views, **stats)


_CID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{30,}$')


def _extract_result_cid(path: str) -> str | None:
    """Return the CID portion of a path if it looks like server output."""
    if not path or not path.startswith('/'):
        return None

    slug = path[1:]
    if not slug or '/' in slug:
        return None

    cid_part = slug.split('.')[0]
    if not cid_part or not _CID_PATTERN.match(cid_part):
        return None

    return cid_part


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

    cid_paths = [f"/{cid}" for cid in request_cids]
    cid_records = (
        CID.query
        .filter(CID.path.in_(cid_paths))
        .all()
    )

    referer_by_cid: Dict[str, str] = {}
    for record in cid_records:
        raw = getattr(record, 'file_data', None)
        if not raw:
            continue

        try:
            payload = json.loads(raw.decode('utf-8'))
        except Exception:
            continue

        referer = _extract_referer_from_headers(payload.get('headers')) if isinstance(payload, dict) else None
        if referer:
            referer_by_cid[record.path.lstrip('/')] = referer

    return referer_by_cid


def _attach_server_event_links(page_views: object) -> None:
    """Annotate page view objects with links to their originating server events."""
    page_view_items = _get_page_view_items(page_views)
    if not page_view_items:
        return

    result_cids = {
        cid
        for cid in (_extract_result_cid(view.path) for view in page_view_items)
        if cid
    }

    if not result_cids:
        return

    invocations = (
        ServerInvocation.query
        .filter(
            ServerInvocation.user_id == current_user.id,
            ServerInvocation.result_cid.in_(result_cids),
        )
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )

    # Prefer the most recent invocation for each result CID.
    invocation_by_result: Dict[str, ServerInvocation] = {}
    for invocation in invocations:
        if not invocation.invocation_cid:
            continue
        if invocation.result_cid not in invocation_by_result:
            invocation_by_result[invocation.result_cid] = invocation

    if not invocation_by_result:
        return

    referer_by_request_cid = _load_request_referers(invocation_by_result.values())

    for view in page_view_items:
        cid = _extract_result_cid(view.path)
        if not cid:
            continue

        invocation = invocation_by_result.get(cid)
        if not invocation:
            continue

        # Attach both the invocation object and helpful links for templates.
        view.server_invocation = invocation
        view.server_invocation_link = f"/{invocation.invocation_cid}.json"

        referer = None
        request_cid = getattr(invocation, 'request_details_cid', None)
        if request_cid:
            referer = referer_by_request_cid.get(request_cid)

        if referer:
            view.server_invocation_referer = referer


__all__ = ['history']
