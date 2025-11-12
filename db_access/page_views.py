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


def count_user_page_views(user_id: str) -> int:
    """Return the number of page views recorded for a user."""
    return PageView.query.filter_by(user_id=user_id).count()  # type: ignore[no-any-return]


def count_unique_page_view_paths(user_id: str) -> int:
    """Return the number of unique paths viewed by a user."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    return (
        db.session.query(func.count(func.distinct(PageView.path)))
        .filter_by(user_id=user_id)
        .scalar()
        or 0
    )


def get_popular_page_paths(user_id: str, limit: int = 5) -> List[Tuple[str, int]]:
    """Return the most frequently viewed paths for a user."""
    # pylint: disable=not-callable  # SQLAlchemy func.count is callable
    return (  # type: ignore[no-any-return]
        db.session.query(PageView.path, func.count(PageView.path).label('count'))
        .filter_by(user_id=user_id)
        .group_by(PageView.path)
        .order_by(func.count(PageView.path).desc())
        .limit(limit)
        .all()
    )


def paginate_user_page_views(user_id: str, page: int, per_page: int = 50) -> Pagination:
    """Return paginated page view history for a user."""
    return (
        PageView.query.filter_by(user_id=user_id)
        .order_by(PageView.viewed_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def count_page_views() -> int:
    """Return the total number of page view records."""
    return PageView.query.count()  # type: ignore[no-any-return]
