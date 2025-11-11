"""Helper class for CID operations."""

from typing import Optional

from cid_presenter import cid_path, format_cid
from db_access import get_cid_by_path


class CidHelper:
    """Centralize CID operations for formatting, normalization, and retrieval."""

    @staticmethod
    def normalize(cid_value: str) -> str:
        """Normalize a CID value to its standard format.

        Args:
            cid_value: The CID value to normalize

        Returns:
            The normalized CID string
        """
        return format_cid(cid_value)

    @staticmethod
    def get_record(cid_value: str):
        """Get a CID record by its value.

        Args:
            cid_value: The CID value to look up

        Returns:
            The CID record if found, None otherwise
        """
        normalized = CidHelper.normalize(cid_value)
        if not normalized:
            return None
        path = cid_path(normalized)
        return get_cid_by_path(path) if path else None

    @staticmethod
    def resolve_size(record, default: int = 0) -> int:
        """Return a best-effort file size from a CID record.

        Args:
            record: The CID record
            default: Default size to return if record is None

        Returns:
            The file size as an integer
        """
        if not record:
            return default

        size = getattr(record, "file_size", None)
        if size is not None:
            return int(size)

        file_data = getattr(record, "file_data", None)
        if file_data:
            return len(file_data)

        return default

    @staticmethod
    def get_path(cid_value: str, extension: Optional[str] = None) -> Optional[str]:
        """Get the full path for a CID, optionally with an extension.

        Args:
            cid_value: The CID value
            extension: Optional file extension (e.g., 'json', 'txt')

        Returns:
            The CID path, or None if invalid
        """
        normalized = CidHelper.normalize(cid_value)
        if not normalized:
            return None
        return cid_path(normalized, extension) if extension else cid_path(normalized)


__all__ = ["CidHelper"]
