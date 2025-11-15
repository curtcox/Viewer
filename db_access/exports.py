"""Database access functions for exports."""
from typing import List

from models import Export
from db_access._common import save_entity


def record_export(cid: str) -> Export:
    """Record an export with the given CID."""
    export = Export(cid=cid)
    save_entity(export)
    return export


def get_exports(limit: int = 100) -> List[Export]:
    """Return the most recent exports ordered from newest to oldest."""
    return (
        Export.query
        .order_by(Export.created_at.desc())
        .limit(limit)
        .all()
    )
