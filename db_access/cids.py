"""CID management operations."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Union

from database import db
import models
from models import Alias, CID, Server
from db_access._common import save_entity, normalize_cid_value
from cid import CID as ValidatedCID, to_cid_string

SaveServerDefinition = Callable[[str, int], str]
StoreServerDefinitions = Callable[[int], str]


@dataclass
class LiteralCIDRecord:
    """Virtual CID record for content embedded directly in a literal CID.

    This class provides an interface compatible with the CID model
    for content that doesn't need to be stored in the database.
    """
    path: str
    file_data: bytes
    file_size: int
    created_at: datetime

    def __repr__(self) -> str:
        return f'<LiteralCID {self.path}>'


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


def _try_resolve_literal_cid(path: str) -> Optional[LiteralCIDRecord]:
    """Try to resolve a literal CID path to a virtual record.

    For CIDs containing literal (embedded) content, this function creates
    a virtual record without database access.

    Args:
        path: CID path (e.g., "/AAAABWhlbGxv")

    Returns:
        LiteralCIDRecord if path is a valid literal CID, None otherwise
    """
    try:
        from cid_core import extract_literal_content  # pylint: disable=import-outside-toplevel
    except (ImportError, ModuleNotFoundError):
        return None

    content = extract_literal_content(path)
    if content is None:
        return None

    return LiteralCIDRecord(
        path=path if path.startswith('/') else f"/{path}",
        file_data=content,
        file_size=len(content),
        created_at=datetime.fromtimestamp(0, timezone.utc),  # Epoch time for immutable content
    )


def get_cid_by_path(path: str) -> Optional[CID | LiteralCIDRecord]:
    """Return a CID record by its path.

    For literal CIDs (content <= 64 bytes embedded in the CID itself),
    returns a virtual LiteralCIDRecord without database access.

    For hash-based CIDs, queries the database for the stored record.

    Args:
        path: CID path (e.g., "/AAAABWhlbGxv")

    Returns:
        CID model instance, LiteralCIDRecord for literal content, or None
    """
    # Try to resolve as literal CID first (no DB access needed)
    literal_record = _try_resolve_literal_cid(path)
    if literal_record is not None:
        return literal_record

    # Fall back to database lookup for hash-based CIDs
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


def create_cid_record_raw(cid: Union[str, ValidatedCID], file_content: bytes) -> CID:
    """Create a new CID record without memory checks (for internal use).
    
    This is a low-level function that bypasses memory checks. Use create_cid_record
    for normal operations, which includes read-only mode memory management.

    Args:
        cid: CID string or ValidatedCID object (will be validated)
        file_content: Content to store

    Returns:
        CID database model instance

    Raises:
        ValueError: If cid is not a valid CID string

    Example:
        >>> record = create_cid_record_raw("AAAAAAAA", b"")
        >>> record = create_cid_record_raw(ValidatedCID("AAAAAAAA"), b"")
    """
    # Validate and normalize the CID
    cid_str = to_cid_string(cid)

    record = CID(
        path=f"/{cid_str}",
        file_data=file_content,
        file_size=len(file_content),
    )
    save_entity(record)
    return record


def create_cid_record(cid: Union[str, ValidatedCID], file_content: bytes) -> CID:
    """Create a new CID record.

    Args:
        cid: CID string or ValidatedCID object (will be validated)
        file_content: Content to store

    Returns:
        CID database model instance

    Raises:
        ValueError: If cid is not a valid CID string
        Aborts with 413 if content is too large in read-only mode

    Example:
        >>> record = create_cid_record("AAAAAAAA", b"")
        >>> record = create_cid_record(ValidatedCID("AAAAAAAA"), b"")
    """
    # Validate and normalize the CID
    cid_str = to_cid_string(cid)
    
    # Check memory limits in read-only mode
    from readonly_config import ReadOnlyConfig  # pylint: disable=import-outside-toplevel
    
    if ReadOnlyConfig.is_read_only_mode():
        from cid_memory_manager import CIDMemoryManager  # pylint: disable=import-outside-toplevel
        
        content_size = len(file_content)
        CIDMemoryManager.check_cid_size(content_size)
        CIDMemoryManager.ensure_memory_available(content_size)

    record = CID(
        path=f"/{cid_str}",
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


def _normalize_cid_input(value: str | ValidatedCID | None) -> str:
    """Return a normalized CID component from string or ValidatedCID input."""
    if isinstance(value, ValidatedCID):
        return value.value
    return normalize_cid_value(value)


def update_cid_references(old_cid: str | ValidatedCID, new_cid: str | ValidatedCID) -> Dict[str, int]:
    """Replace CID references in alias and server definitions.

    Parameters
    ----------
    old_cid:
        The previous CID value, supplied as a string or :class:`cid.CID`.
        Leading slashes are ignored for string values.
    new_cid:
        The CID that should replace the previous value, supplied as a string
        or :class:`cid.CID`. Leading slashes are ignored for string values.

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

    normalized_old = _normalize_cid_input(old_cid)
    normalized_new = _normalize_cid_input(new_cid)

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
