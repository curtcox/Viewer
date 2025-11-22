# db_config.py
"""Database configuration module for managing different database modes."""

from enum import Enum
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class DatabaseMode(Enum):
    """Enum for database operation modes."""

    DISK = "disk"
    MEMORY = "memory"


class MemoryLimitExceededError(Exception):
    """Raised when the in-memory database exceeds its memory limit."""


class DatabaseConfig:
    """Centralized database configuration manager."""

    _instance: Optional["DatabaseConfig"] = None
    _mode: DatabaseMode = DatabaseMode.DISK

    # Hardcoded memory limit for in-memory database (100 MB)
    MEMORY_LIMIT_BYTES: int = 100 * 1024 * 1024

    @classmethod
    def get_instance(cls) -> "DatabaseConfig":
        """Get the singleton instance of DatabaseConfig."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_mode(cls, mode: DatabaseMode) -> None:
        """Set the database mode."""
        cls._mode = mode
        if mode == DatabaseMode.MEMORY:
            logger.warning("Using memory-only database")

    @classmethod
    def get_mode(cls) -> DatabaseMode:
        """Get the current database mode."""
        return cls._mode

    @classmethod
    def is_memory_mode(cls) -> bool:
        """Check if running in memory mode."""
        return cls._mode == DatabaseMode.MEMORY

    @classmethod
    def get_database_uri(cls) -> str:
        """Get the database URI based on current mode."""
        if cls._mode == DatabaseMode.MEMORY:
            return "sqlite:///:memory:"
        return os.environ.get("DATABASE_URL", "sqlite:///secureapp.db")

    @classmethod
    def check_memory_limit(cls, current_usage_bytes: int) -> None:
        """
        Check if memory usage exceeds the limit.

        Raises MemoryLimitExceededError if exceeded.
        """
        if (
            cls._mode == DatabaseMode.MEMORY
            and current_usage_bytes > cls.MEMORY_LIMIT_BYTES
        ):
            raise MemoryLimitExceededError(
                f"In-memory database exceeded limit: "
                f"{current_usage_bytes} bytes > {cls.MEMORY_LIMIT_BYTES} bytes"
            )

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults (useful for testing)."""
        cls._mode = DatabaseMode.DISK
