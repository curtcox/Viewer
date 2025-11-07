"""Analytics and page view tracking helpers for the Flask app."""

from typing import Any, Dict

from flask import Response, request, session
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import SQLAlchemyError

from db_access import (
    count_unique_page_view_paths,
    count_user_page_views,
    get_popular_page_paths,
    paginate_user_page_views,
    rollback_session,
    save_page_view,
)
from identity import current_user
from models import PageView  # noqa: F401


def make_session_permanent() -> None:
    """Ensure the user's session is marked as permanent."""
    session.permanent = True


def should_track_page_view(response: Response) -> bool:
    """Determine if the current request should be tracked."""
    if response.status_code != 200:
        return False

    # Skip tracking for static files, API calls, and certain paths
    skip_paths = ['/static/', '/favicon.ico', '/robots.txt', '/api/', '/_']
    if any(request.path.startswith(skip) for skip in skip_paths):
        return False

    # Skip tracking AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return False

    return True


def create_page_view_record() -> PageView:
    """Create a page view record for the current request."""
    return PageView(
        user_id=current_user.id,
        path=request.path,
        method=request.method,
        user_agent=request.headers.get('User-Agent', '')[:500],
        ip_address=request.remote_addr,
    )


def track_page_view(response: Response) -> Response:
    """Track page views for authenticated users."""
    try:
        if should_track_page_view(response):
            page_view = create_page_view_record()
            save_page_view(page_view)
    except (SQLAlchemyError, AttributeError, RuntimeError):
        # Don't let tracking errors break the request (database, attribute, or runtime errors)
        rollback_session()

    return response


def get_user_history_statistics(user_id: str) -> Dict[str, Any]:
    """Calculate history statistics for a user."""
    # Get total views count
    total_views = count_user_page_views(user_id)

    # Get unique paths count
    unique_paths = count_unique_page_view_paths(user_id)

    # Get most visited paths
    popular_paths = get_popular_page_paths(user_id)

    return {
        'total_views': total_views,
        'unique_paths': unique_paths,
        'popular_paths': popular_paths,
    }


def get_paginated_page_views(user_id: str, page: int, per_page: int = 50) -> Pagination:
    """Get paginated page views for a user."""
    return paginate_user_page_views(user_id, page, per_page=per_page)


__all__ = [
    'make_session_permanent',
    'should_track_page_view',
    'create_page_view_record',
    'track_page_view',
    'get_user_history_statistics',
    'get_paginated_page_views',
]
