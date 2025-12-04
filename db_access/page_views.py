"""Page view tracking and analytics."""

from typing import List, Tuple

from datetime import datetime

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func

from database import db
from models import PageView
from db_access._common import save_entity


def save_page_view(page_view: PageView) -> PageView:
    """Persist a page view record."""
    return save_entity(page_view)


def _apply_time_bounds(query, start: datetime | None, end: datetime | None):
    """Apply optional start/end filters to a PageView query."""
    if start:
        query = query.filter(PageView.viewed_at >= start)
    if end:
        query = query.filter(PageView.viewed_at <= end)
    return query


def count_unique_page_view_paths(start: datetime | None = None, end: datetime | None = None) -> int:
    """Return the number of unique paths viewed."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    query = db.session.query(func.count(func.distinct(PageView.path)))
    query = _apply_time_bounds(query, start, end)
    return query.scalar() or 0


def get_popular_page_paths(
    limit: int = 5,
    start: datetime | None = None,
    end: datetime | None = None,
) -> List[Tuple[str, int]]:
    """Return the most frequently viewed paths."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    query = db.session.query(PageView.path, func.count(PageView.path).label('count'))
    query = _apply_time_bounds(query, start, end)

    return (
        query
        .group_by(PageView.path)
        .order_by(func.count(PageView.path).desc())
        .limit(limit)
        .all()
    )


def paginate_page_views(
    page: int,
    per_page: int = 50,
    start: datetime | None = None,
    end: datetime | None = None,
) -> Pagination:
    """Return paginated page view history."""
    query = _apply_time_bounds(PageView.query, start, end)
    return query.order_by(PageView.viewed_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


def count_page_views(start: datetime | None = None, end: datetime | None = None) -> int:
    """Return the total number of page view records."""
    query = _apply_time_bounds(PageView.query, start, end)
    return query.count()
