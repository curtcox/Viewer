"""Analytics and page view tracking helpers for the Flask app."""

from flask import request, session
from flask import request, session

from identity import current_user

from models import PageView, ServerInvocation  # noqa: F401


def make_session_permanent():
    """Ensure the user's session is marked as permanent."""
    session.permanent = True


def should_track_page_view(response):
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


def create_page_view_record():
    """Create a page view record for the current request."""
    return PageView(
        user_id=current_user.id,
        path=request.path,
        method=request.method,
        user_agent=request.headers.get('User-Agent', '')[:500],
        ip_address=request.remote_addr,
    )


def track_page_view(response):
    """Track page views for authenticated users."""
    try:
        if should_track_page_view(response):
            page_view = create_page_view_record()
            from database import db
            db.session.add(page_view)
            db.session.commit()
    except Exception:
        # Don't let tracking errors break the request
        from database import db
        db.session.rollback()

    return response


def get_user_history_statistics(user_id):
    """Calculate history statistics for a user."""
    from sqlalchemy import func
    from database import db

    # Get total views count
    total_views = PageView.query.filter_by(user_id=user_id).count()

    # Get unique paths count
    unique_paths = (
        db.session.query(func.count(func.distinct(PageView.path)))
        .filter_by(user_id=user_id)
        .scalar()
    )

    # Get most visited paths
    popular_paths = (
        db.session.query(PageView.path, func.count(PageView.path).label('count'))
        .filter_by(user_id=user_id)
        .group_by(PageView.path)
        .order_by(func.count(PageView.path).desc())
        .limit(5)
        .all()
    )

    return {
        'total_views': total_views,
        'unique_paths': unique_paths,
        'popular_paths': popular_paths,
    }


def get_paginated_page_views(user_id, page, per_page=50):
    """Get paginated page views for a user."""
    return (
        PageView.query.filter_by(user_id=user_id)
        .order_by(PageView.viewed_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


__all__ = [
    'make_session_permanent',
    'should_track_page_view',
    'create_page_view_record',
    'track_page_view',
    'get_user_history_statistics',
    'get_paginated_page_views',
]
