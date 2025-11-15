"""Page view tracking and analytics."""

from typing import List, Tuple

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func

from database import db
from models import PageView
from db_access._common import save_entity


def save_page_view(page_view: PageView) -> PageView:
    """Persist a page view record."""
    return save_entity(page_view)


def count_unique_page_view_paths() -> int:
    """Return the number of unique paths viewed."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    return (
        db.session.query(func.count(func.distinct(PageView.path)))
        .scalar()
        or 0
    )


def get_popular_page_paths(limit: int = 5) -> List[Tuple[str, int]]:
    """Return the most frequently viewed paths."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    return (
        db.session.query(PageView.path, func.count(PageView.path).label('count'))
        .group_by(PageView.path)
        .order_by(func.count(PageView.path).desc())
        .limit(limit)
        .all()
    )


def paginate_page_views(page: int, per_page: int = 50) -> Pagination:
    """Return paginated page view history."""
    return (
        PageView.query
        .order_by(PageView.viewed_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def count_page_views() -> int:
    """Return the total number of page view records."""
    return PageView.query.count()
