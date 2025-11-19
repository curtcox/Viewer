# tests/test_cli_args.py
"""Tests for CLI argument parsing."""

import sys
from unittest.mock import patch

import pytest

from cli_args import configure_from_args, parse_arguments
from db_config import DatabaseConfig, DatabaseMode


class TestParseArguments:
    """Tests for parse_arguments function."""

    def test_default_arguments(self):
        """Default arguments should have expected values."""
        with patch.object(sys, "argv", ["app.py"]):
            args = parse_arguments()
            assert args.in_memory_db is False
            assert args.port == 5000
            assert args.host == "127.0.0.1"
            assert args.debug is False

    def test_in_memory_db_flag(self):
        """--in-memory-db flag should set in_memory_db to True."""
        with patch.object(sys, "argv", ["app.py", "--in-memory-db"]):
            args = parse_arguments()
            assert args.in_memory_db is True

    def test_port_argument(self):
        """--port should set custom port."""
        with patch.object(sys, "argv", ["app.py", "--port", "8080"]):
            args = parse_arguments()
            assert args.port == 8080

    def test_host_argument(self):
        """--host should set custom host."""
        with patch.object(sys, "argv", ["app.py", "--host", "0.0.0.0"]):
            args = parse_arguments()
            assert args.host == "0.0.0.0"

    def test_debug_flag(self):
        """--debug flag should enable debug mode."""
        with patch.object(sys, "argv", ["app.py", "--debug"]):
            args = parse_arguments()
            assert args.debug is True

    def test_multiple_arguments(self):
        """Multiple arguments should all be parsed."""
        with patch.object(
            sys, "argv", ["app.py", "--in-memory-db", "--port", "3000", "--debug"]
        ):
            args = parse_arguments()
            assert args.in_memory_db is True
            assert args.port == 3000
            assert args.debug is True


class TestConfigureFromArgs:
    """Tests for configure_from_args function."""

    def setup_method(self):
        """Reset config before each test."""
        DatabaseConfig.reset()

    def test_configure_from_args_sets_memory_mode(self):
        """Should set memory mode when flag is set."""
        with patch.object(sys, "argv", ["app.py", "--in-memory-db"]):
            args = parse_arguments()
            configure_from_args(args)
            assert DatabaseConfig.is_memory_mode()

    def test_configure_from_args_keeps_disk_mode(self):
        """Should keep disk mode when flag is not set."""
        with patch.object(sys, "argv", ["app.py"]):
            args = parse_arguments()
            configure_from_args(args)
            assert not DatabaseConfig.is_memory_mode()

    def test_memory_mode_takes_precedence_over_env(self, monkeypatch):
        """CLI flag should take precedence over DATABASE_URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/testdb")
        with patch.object(sys, "argv", ["app.py", "--in-memory-db"]):
            args = parse_arguments()
            configure_from_args(args)
            assert DatabaseConfig.is_memory_mode()
            assert DatabaseConfig.get_database_uri() == "sqlite:///:memory:"
