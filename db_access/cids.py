"""CID management operations."""

from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

from database import db
import models
from models import Alias, CID, Server
from db_access._common import save_entity, normalize_cid_value

SaveServerDefinition = Callable[[str, int], str]
StoreServerDefinitions = Callable[[int], str]


def _require_cid_utilities() -> tuple[SaveServerDefinition, StoreServerDefinitions]:
    """Return CID helper functions or raise if unavailable."""

    try:
        from cid_utils import (  # pylint: disable=import-outside-toplevel
            save_server_definition_as_cid,
            store_server_definitions_cid,
        )
    except (ImportError, ModuleNotFoundError, RuntimeError) as exc:  # pragma: no cover - defensive
        raise RuntimeError("CID utilities are unavailable") from exc

    return save_server_definition_as_cid, store_server_definitions_cid


def get_cid_by_path(path: str) -> Optional[CID]:
    """Return a CID record by its path."""
    return CID.query.filter_by(path=path).first()


def find_cids_by_prefix(prefix: str) -> List[CID]:
    """Return CID records whose path matches the given CID prefix."""
    if not prefix:
        return []

    normalized = prefix.split('.')[0].lstrip('/')
    if not normalized:
        return []

    pattern = f"/{normalized}%"
    return (
        CID.query
        .filter(CID.path.like(pattern))
        .order_by(CID.path.asc())
        .all()
    )


def create_cid_record(cid: str, file_content: bytes) -> CID:
    """Create a new CID record."""
    record = CID(
        path=f"/{cid}",
        file_data=file_content,
        file_size=len(file_content),
    )
    save_entity(record)
    return record


def get_uploads() -> List[CID]:
    """Return all CID uploads ordered from newest to oldest."""
    session_provider = getattr(models, "db", None)
    if session_provider is not None and hasattr(session_provider, "session"):
        query = session_provider.session.query
    else:
        query = db.session.query

    return (
        query(CID)
        .order_by(CID.created_at.desc())
        .all()
    )


def get_cids_by_paths(paths: Iterable[str]) -> List[CID]:
    """Return CID records that match any of the supplied paths."""
    normalized_paths = [path for path in paths if path]
    if not normalized_paths:
        return []

    return CID.query.filter(CID.path.in_(normalized_paths)).all()


def get_recent_cids(limit: int = 10) -> List[CID]:
    """Return the most recent CID records."""
    return (
        CID.query
        .order_by(CID.created_at.desc())
        .limit(limit)
        .all()
    )


def get_first_cid() -> Optional[CID]:
    """Return the first CID record in the table."""
    return CID.query.first()


def count_cids() -> int:
    """Return the total number of CID records."""
    return CID.query.count()


def update_cid_references(old_cid: str, new_cid: str) -> Dict[str, int]:
    """Replace CID references in alias and server definitions.

    Parameters
    ----------
    old_cid:
        The previous CID value. Leading slashes are ignored.
    new_cid:
        The CID that should replace the previous value. Leading slashes are ignored.

    Returns
    -------
    Dict[str, int]
        A mapping containing the counts of updated aliases and servers.

    Side effects:
        - Commits database changes
        - Regenerates server definition CIDs
        - Calls store_server_definitions_cid() for affected users
    """

    save_definition, store_definitions = _require_cid_utilities()

    normalized_old = normalize_cid_value(old_cid)
    normalized_new = normalize_cid_value(new_cid)

    if not normalized_old or not normalized_new or normalized_old == normalized_new:
        return {"aliases": 0, "servers": 0}

    old_path = f"/{normalized_old}"
    new_path = f"/{normalized_new}"

    alias_updates = 0
    server_updates = 0
    now = datetime.now(timezone.utc)

    aliases: List[Alias] = Alias.query.all()
    for alias in aliases:
        alias_changed = False

        original_definition = alias.definition
        updated_definition, definition_changed = _replace_cid_text(
            original_definition,
            old_path,
            new_path,
            normalized_old,
            normalized_new,
        )
        if definition_changed:
            alias.definition = updated_definition
            alias_changed = True

        if alias_changed:
            alias.updated_at = now
            alias_updates += 1

    servers: List[Server] = Server.query.all()
    if servers:
        for server in servers:
            updated_definition, definition_changed = _replace_cid_text(
                server.definition,
                old_path,
                new_path,
                normalized_old,
                normalized_new,
            )
            if definition_changed:
                server.definition = updated_definition
                server.definition_cid = save_definition(updated_definition)
                server.updated_at = now
                server_updates += 1

    total_updates = alias_updates + server_updates
    if not total_updates:
        return {"aliases": 0, "servers": 0}

    db.session.commit()

    if server_updates:
        store_definitions()

    return {"aliases": alias_updates, "servers": server_updates}


def _replace_cid_text(
    text: Optional[str],
    old_path: str,
    new_path: str,
    old_value: str,
    new_value: str,
) -> tuple[Optional[str], bool]:
    """Return text with CID references replaced and whether a change occurred."""
    if text is None:
        return None, False

    updated = text.replace(old_path, new_path).replace(old_value, new_value)
    if updated == text:
        return text, False
    return updated, True
