# tests/test_db_snapshot.py
"""Tests for the database snapshot module."""

import json
import os

import pytest

from database import db
from db_config import DatabaseConfig, DatabaseMode
from db_snapshot import DatabaseSnapshot
from models import Server


@pytest.mark.memory_db
class TestDatabaseSnapshot:
    """Tests for DatabaseSnapshot class."""

    def setup_method(self):
        """Reset config before each test."""
        DatabaseConfig.reset()

    def test_create_snapshot_requires_memory_mode(self, disk_db_app):
        """Snapshot creation should fail in disk mode."""
        with disk_db_app.app_context():
            with pytest.raises(RuntimeError) as exc_info:
                DatabaseSnapshot.create_snapshot()
            assert "memory mode" in str(exc_info.value)

    def test_create_snapshot_saves_data(self, memory_db_app, tmp_path):
        """Snapshot should save current database state."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            # Add test data
            server = Server(name="test-server", definition="test def")
            db.session.add(server)
            db.session.commit()

            # Create snapshot
            path = DatabaseSnapshot.create_snapshot("test_snap")

            # Verify file exists
            assert os.path.exists(path)

            # Verify content
            with open(path) as f:
                data = json.load(f)

            assert "servers" in data["tables"]
            assert len(data["tables"]["servers"]) == 1
            assert data["tables"]["servers"][0]["name"] == "test-server"

    def test_create_snapshot_auto_name(self, memory_db_app, tmp_path):
        """Snapshot should generate name if not provided."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            path = DatabaseSnapshot.create_snapshot()
            assert os.path.exists(path)
            # Name should be timestamp-based
            filename = os.path.basename(path)
            assert filename.endswith(".json")
            assert len(filename) > 10  # Timestamp is reasonably long

    def test_list_snapshots(self, memory_db_app, tmp_path):
        """Should list all available snapshots."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            DatabaseSnapshot.create_snapshot("snap1")
            DatabaseSnapshot.create_snapshot("snap2")

            snapshots = DatabaseSnapshot.list_snapshots()
            assert "snap1" in snapshots
            assert "snap2" in snapshots

    def test_list_snapshots_empty(self, memory_db_app, tmp_path):
        """Should return empty list when no snapshots exist."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path / "nonexistent")

        with memory_db_app.app_context():
            snapshots = DatabaseSnapshot.list_snapshots()
            assert snapshots == []

    def test_delete_snapshot(self, memory_db_app, tmp_path):
        """Should delete snapshot by name."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            DatabaseSnapshot.create_snapshot("to_delete")
            assert DatabaseSnapshot.delete_snapshot("to_delete")
            assert "to_delete" not in DatabaseSnapshot.list_snapshots()

    def test_delete_nonexistent_snapshot(self, memory_db_app, tmp_path):
        """Should return False when deleting nonexistent snapshot."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            assert not DatabaseSnapshot.delete_snapshot("nonexistent")

    def test_get_snapshot_info(self, memory_db_app, tmp_path):
        """Should return snapshot information."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            # Add test data
            server = Server(name="test-server", definition="test def")
            db.session.add(server)
            db.session.commit()

            DatabaseSnapshot.create_snapshot("info_test")

            info = DatabaseSnapshot.get_snapshot_info("info_test")
            assert info is not None
            assert info["name"] == "info_test"
            assert "created_at" in info
            assert info["tables"]["servers"] == 1

    def test_get_snapshot_info_nonexistent(self, memory_db_app, tmp_path):
        """Should return None for nonexistent snapshot."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            info = DatabaseSnapshot.get_snapshot_info("nonexistent")
            assert info is None

    def test_snapshot_preserves_all_tables(self, memory_db_app, tmp_path):
        """Snapshot should include all table types."""
        DatabaseSnapshot.SNAPSHOT_DIR = str(tmp_path)

        with memory_db_app.app_context():
            DatabaseSnapshot.create_snapshot("all_tables")

            with open(tmp_path / "all_tables.json") as f:
                data = json.load(f)

            expected_tables = [
                "servers",
                "aliases",
                "variables",
                "secrets",
                "page_views",
                "entity_interactions",
                "server_invocations",
                "exports",
                "cids",
            ]

            for table in expected_tables:
                assert table in data["tables"], f"Missing table: {table}"
