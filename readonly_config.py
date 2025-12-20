# readonly_config.py
"""Read-only mode configuration for the Viewer application."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ReadOnlyConfig:
    """Centralized read-only mode configuration manager."""

    _instance: Optional["ReadOnlyConfig"] = None
    _read_only_mode: bool = False
    _max_cid_memory_bytes: int = 1 * 1024 * 1024 * 1024  # Default: 1GB

    @classmethod
    def get_instance(cls) -> "ReadOnlyConfig":
        """Get the singleton instance of ReadOnlyConfig."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_read_only_mode(cls, enabled: bool) -> None:
        """Set the read-only mode.

        Args:
            enabled: Whether to enable read-only mode
        """
        cls._read_only_mode = enabled
        if enabled:
            logger.warning("Application running in READ-ONLY mode")

    @classmethod
    def is_read_only_mode(cls) -> bool:
        """Check if running in read-only mode."""
        return cls._read_only_mode

    @classmethod
    def set_max_cid_memory(cls, max_bytes: int) -> None:
        """Set the maximum CID memory size.

        Args:
            max_bytes: Maximum bytes for CID storage
        """
        cls._max_cid_memory_bytes = max_bytes
        logger.info("Max CID memory set to %d bytes", max_bytes)

    @classmethod
    def get_max_cid_memory(cls) -> int:
        """Get the maximum CID memory size in bytes."""
        return cls._max_cid_memory_bytes

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults (useful for testing)."""
        cls._read_only_mode = False
        cls._max_cid_memory_bytes = 1 * 1024 * 1024 * 1024
