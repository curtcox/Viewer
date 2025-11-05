"""Database access functions for exports."""
from typing import List

from models import Export
from db_access._common import save_entity


def record_export(user_id: str, cid: str) -> Export:
    """Record an export with the given user ID and CID."""
    export = Export(user_id=user_id, cid=cid)
    save_entity(export)
    return export


def get_user_exports(user_id: str, limit: int = 100) -> List[Export]:
    """Return the most recent exports for a user ordered from newest to oldest."""
    return (
        Export.query
        .filter(Export.user_id == user_id)
        .order_by(Export.created_at.desc())
        .limit(limit)
        .all()
    )

