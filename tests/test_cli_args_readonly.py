# tests/test_cli_args_readonly.py
"""Tests for read-only mode CLI argument parsing."""

import sys
from unittest.mock import patch

import pytest

from cli_args import configure_from_args, parse_arguments, parse_memory_size
from db_config import DatabaseConfig
from readonly_config import ReadOnlyConfig


class TestParseMemorySize:
    """Tests for parse_memory_size function."""

    def test_parse_bytes(self):
        """Should parse plain byte values."""
        assert parse_memory_size("1024") == 1024
        assert parse_memory_size("500") == 500

    def test_parse_kilobytes(self):
        """Should parse kilobyte values."""
        assert parse_memory_size("1K") == 1024
        assert parse_memory_size("10K") == 10 * 1024
        assert parse_memory_size("1KB") == 1024

    def test_parse_megabytes(self):
        """Should parse megabyte values."""
        assert parse_memory_size("1M") == 1024 * 1024
        assert parse_memory_size("100M") == 100 * 1024 * 1024
        assert parse_memory_size("1MB") == 1024 * 1024

    def test_parse_gigabytes(self):
        """Should parse gigabyte values."""
        assert parse_memory_size("1G") == 1024 * 1024 * 1024
        assert parse_memory_size("2G") == 2 * 1024 * 1024 * 1024
        assert parse_memory_size("1GB") == 1024 * 1024 * 1024

    def test_parse_terabytes(self):
        """Should parse terabyte values."""
        assert parse_memory_size("1T") == 1024 * 1024 * 1024 * 1024
        assert parse_memory_size("1TB") == 1024 * 1024 * 1024 * 1024

    def test_parse_decimal_values(self):
        """Should parse decimal values."""
        assert parse_memory_size("0.5G") == int(0.5 * 1024 * 1024 * 1024)
        assert parse_memory_size("1.5M") == int(1.5 * 1024 * 1024)

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert parse_memory_size("1g") == 1024 * 1024 * 1024
        assert parse_memory_size("100m") == 100 * 1024 * 1024

    def test_whitespace_handling(self):
        """Should handle whitespace."""
        assert parse_memory_size(" 1G ") == 1024 * 1024 * 1024
        assert parse_memory_size("100 M") == 100 * 1024 * 1024

    def test_invalid_format(self):
        """Should raise ValueError for invalid formats."""
        with pytest.raises(ValueError, match="Invalid memory size format"):
            parse_memory_size("invalid")

        with pytest.raises(ValueError, match="Invalid memory size format"):
            parse_memory_size("1X")


class TestReadOnlyModeArguments:
    """Tests for read-only mode CLI arguments."""

    def setup_method(self):
        """Reset config before each test."""
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()

    def test_read_only_flag(self):
        """--read-only flag should be parsed."""
        with patch.object(sys, "argv", ["app.py", "--read-only"]):
            args = parse_arguments()
            assert args.read_only is True

    def test_max_cid_memory_default(self):
        """--max-cid-memory should default to 1G."""
        with patch.object(sys, "argv", ["app.py"]):
            args = parse_arguments()
            assert args.max_cid_memory == "1G"

    def test_max_cid_memory_custom(self):
        """--max-cid-memory should accept custom values."""
        with patch.object(sys, "argv", ["app.py", "--max-cid-memory", "512M"]):
            args = parse_arguments()
            assert args.max_cid_memory == "512M"

    def test_configure_read_only_mode(self):
        """configure_from_args should enable read-only mode."""
        with patch.object(sys, "argv", ["app.py", "--read-only"]):
            args = parse_arguments()
            configure_from_args(args)

            assert ReadOnlyConfig.is_read_only_mode() is True
            assert DatabaseConfig.is_memory_mode() is True

    def test_configure_max_cid_memory(self):
        """configure_from_args should set max CID memory."""
        with patch.object(
            sys, "argv", ["app.py", "--read-only", "--max-cid-memory", "512M"]
        ):
            args = parse_arguments()
            configure_from_args(args)

            assert ReadOnlyConfig.get_max_cid_memory() == 512 * 1024 * 1024

    def test_configure_invalid_max_cid_memory(self):
        """configure_from_args should raise ValueError for invalid memory size."""
        with patch.object(
            sys, "argv", ["app.py", "--read-only", "--max-cid-memory", "invalid"]
        ):
            args = parse_arguments()

            with pytest.raises(ValueError, match="Invalid --max-cid-memory value"):
                configure_from_args(args)
