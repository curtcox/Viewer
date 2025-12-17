# tests/test_readonly_config.py
"""Tests for read-only mode configuration."""

import pytest

from readonly_config import ReadOnlyConfig


class TestReadOnlyConfig:
    """Tests for ReadOnlyConfig class."""

    def setup_method(self):
        """Reset config before each test."""
        ReadOnlyConfig.reset()

    def test_default_state(self):
        """Default state should be read-write mode."""
        assert ReadOnlyConfig.is_read_only_mode() is False

    def test_enable_read_only_mode(self):
        """Should be able to enable read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        assert ReadOnlyConfig.is_read_only_mode() is True

    def test_disable_read_only_mode(self):
        """Should be able to disable read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_read_only_mode(False)
        assert ReadOnlyConfig.is_read_only_mode() is False

    def test_default_max_cid_memory(self):
        """Default max CID memory should be 1GB."""
        assert ReadOnlyConfig.get_max_cid_memory() == 1 * 1024 * 1024 * 1024

    def test_set_max_cid_memory(self):
        """Should be able to set custom max CID memory."""
        custom_size = 512 * 1024 * 1024  # 512MB
        ReadOnlyConfig.set_max_cid_memory(custom_size)
        assert ReadOnlyConfig.get_max_cid_memory() == custom_size

    def test_reset(self):
        """Reset should restore defaults."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_max_cid_memory(100)
        
        ReadOnlyConfig.reset()
        
        assert ReadOnlyConfig.is_read_only_mode() is False
        assert ReadOnlyConfig.get_max_cid_memory() == 1 * 1024 * 1024 * 1024
