"""Database access functions for exports."""

from typing import List, Union

from cid import CID as ValidatedCID
from models import Export
from db_access._common import save_entity


def record_export(cid: Union[str, ValidatedCID]) -> Export:
    """Record an export with the given CID.

    The ``cid`` argument may be supplied as either a raw CID string or a
    validated :class:`cid.CID` instance.  In both cases the normalized string
    value is persisted.
    """
    cid_value = cid.value if isinstance(cid, ValidatedCID) else cid
    export = Export(cid=cid_value)
    save_entity(export)
    return export


def get_exports(limit: int = 100) -> List[Export]:
    """Return the most recent exports ordered from newest to oldest."""
    return Export.query.order_by(Export.created_at.desc()).limit(limit).all()
