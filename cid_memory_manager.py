# cid_memory_manager.py
"""CID memory management for read-only mode."""

import logging
from typing import Optional

from flask import abort
from sqlalchemy import func

from database import db
from models import CID
from readonly_config import ReadOnlyConfig

logger = logging.getLogger(__name__)


class CIDMemoryManager:
    """Manage CID storage within memory limits in read-only mode."""

    @staticmethod
    def get_total_cid_size() -> int:
        """Calculate total size of all CIDs in memory.

        Returns:
            Total size in bytes
        """
        result = db.session.query(func.sum(CID.file_size)).scalar()
        return result or 0

    @staticmethod
    def check_cid_size(content_size: int) -> None:
        """Check if a CID would exceed memory limits.

        Args:
            content_size: Size of content to store

        Raises:
            Aborts with 413 if content is too large
        """
        if not ReadOnlyConfig.is_read_only_mode():
            return

        max_memory = ReadOnlyConfig.get_max_cid_memory()

        # Check if single CID exceeds limit
        if content_size > max_memory:
            logger.warning(
                "CID size %d exceeds max memory limit %d", content_size, max_memory
            )
            abort(413, description="Content too large for read-only mode memory limit")

    @staticmethod
    def ensure_memory_available(required_bytes: int) -> None:
        """Ensure enough memory is available by evicting largest CIDs if needed.

        Args:
            required_bytes: Bytes needed for new CID
        """
        if not ReadOnlyConfig.is_read_only_mode():
            return

        max_memory = ReadOnlyConfig.get_max_cid_memory()
        current_size = CIDMemoryManager.get_total_cid_size()
        available = max_memory - current_size

        if required_bytes <= available:
            return

        # Need to free up space - delete largest CIDs until we have enough room
        needed = required_bytes - available
        freed = 0

        logger.info(
            "Need to free %d bytes for new CID (current: %d, max: %d)",
            needed,
            current_size,
            max_memory,
        )

        evicted = 0
        while freed < needed:
            # Find the largest CID
            largest = CID.query.order_by(CID.file_size.desc()).first()

            if not largest:
                # No more CIDs to delete
                logger.error("Cannot free enough memory for new CID")
                abort(413, description="Cannot free enough memory for new CID")

            freed_size = largest.file_size or 0
            logger.info("Evicting CID %s (size: %d bytes)", largest.path, freed_size)

            db.session.delete(largest)
            freed += freed_size
            evicted += 1

        db.session.commit()
        logger.info("Freed %d bytes by evicting %d CID(s)", freed, evicted)

    @staticmethod
    def store_cid_with_limit_check(cid_path: str, content: bytes) -> Optional[CID]:
        """Store a CID with memory limit checks.

        Args:
            cid_path: Path for the CID
            content: Content bytes to store

        Returns:
            CID record if stored successfully, None otherwise

        Raises:
            Aborts with 413 if content is too large
        """
        content_size = len(content)

        # Check if single CID is too large
        CIDMemoryManager.check_cid_size(content_size)

        # Ensure we have enough memory available
        CIDMemoryManager.ensure_memory_available(content_size)

        # Create the CID record using raw function to avoid duplicate checks
        from db_access.cids import create_cid_record_raw  # pylint: disable=import-outside-toplevel

        # Extract CID from path (remove leading /)
        cid_value = cid_path.lstrip("/")
        return create_cid_record_raw(cid_value, content)
