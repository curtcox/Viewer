# tests/test_db_config.py
"""Tests for the database configuration module."""

import logging
import os

import pytest

from db_config import DatabaseConfig, DatabaseMode, MemoryLimitExceededError


class TestDatabaseConfig:
    """Tests for DatabaseConfig class."""

    def setup_method(self):
        """Reset config before each test."""
        DatabaseConfig.reset()

    def test_default_mode_is_disk(self):
        """Default mode should be disk."""
        assert DatabaseConfig.get_mode() == DatabaseMode.DISK

    def test_set_memory_mode(self):
        """Should be able to set memory mode."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert DatabaseConfig.get_mode() == DatabaseMode.MEMORY
        assert DatabaseConfig.is_memory_mode()

    def test_set_disk_mode(self):
        """Should be able to set disk mode."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        assert DatabaseConfig.get_mode() == DatabaseMode.DISK
        assert not DatabaseConfig.is_memory_mode()

    def test_get_database_uri_disk_mode(self):
        """Disk mode should return file-based URI."""
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        uri = DatabaseConfig.get_database_uri()
        assert "memory" not in uri

    def test_get_database_uri_disk_mode_with_env_var(self, monkeypatch):
        """Disk mode should use DATABASE_URL if set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/testdb")
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        uri = DatabaseConfig.get_database_uri()
        assert uri == "postgresql://localhost/testdb"

    def test_get_database_uri_memory_mode(self):
        """Memory mode should return in-memory URI."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert DatabaseConfig.get_database_uri() == "sqlite:///:memory:"

    def test_get_database_uri_memory_mode_ignores_env_var(self, monkeypatch):
        """Memory mode should ignore DATABASE_URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/testdb")
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert DatabaseConfig.get_database_uri() == "sqlite:///:memory:"

    def test_reset_returns_to_disk_mode(self):
        """Reset should return to disk mode."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        DatabaseConfig.reset()
        assert DatabaseConfig.get_mode() == DatabaseMode.DISK

    def test_memory_limit_not_exceeded(self):
        """Should not raise when under limit."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        # Should not raise
        DatabaseConfig.check_memory_limit(50 * 1024 * 1024)  # 50 MB

    def test_memory_limit_exceeded_raises_error(self):
        """Should raise MemoryLimitExceededError when limit exceeded."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        with pytest.raises(MemoryLimitExceededError):
            DatabaseConfig.check_memory_limit(200 * 1024 * 1024)  # 200 MB

    def test_memory_limit_at_boundary(self):
        """Should not raise at exactly the limit."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        # Should not raise at exactly limit
        DatabaseConfig.check_memory_limit(DatabaseConfig.MEMORY_LIMIT_BYTES)

    def test_memory_limit_just_over_boundary(self):
        """Should raise when just over limit."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        with pytest.raises(MemoryLimitExceededError):
            DatabaseConfig.check_memory_limit(DatabaseConfig.MEMORY_LIMIT_BYTES + 1)

    def test_memory_limit_not_checked_in_disk_mode(self):
        """Should not raise in disk mode even with high value."""
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        # Should not raise even with very high value
        DatabaseConfig.check_memory_limit(1000 * 1024 * 1024)  # 1 GB

    def test_startup_warning_logged(self, caplog):
        """Should log warning when entering memory mode."""
        with caplog.at_level(logging.WARNING):
            DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert "Using memory-only database" in caplog.text

    def test_no_warning_for_disk_mode(self, caplog):
        """Should not log warning when entering disk mode."""
        with caplog.at_level(logging.WARNING):
            DatabaseConfig.set_mode(DatabaseMode.DISK)
        assert "Using memory-only database" not in caplog.text

    def test_get_instance_returns_singleton(self):
        """get_instance should return the same instance."""
        instance1 = DatabaseConfig.get_instance()
        instance2 = DatabaseConfig.get_instance()
        assert instance1 is instance2

    def test_memory_limit_error_message(self):
        """Error message should contain usage details."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        usage = 200 * 1024 * 1024
        with pytest.raises(MemoryLimitExceededError) as exc_info:
            DatabaseConfig.check_memory_limit(usage)
        error_msg = str(exc_info.value)
        assert str(usage) in error_msg
        assert str(DatabaseConfig.MEMORY_LIMIT_BYTES) in error_msg
