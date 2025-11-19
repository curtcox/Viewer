# tests/test_db_edge_cases_equivalence.py
"""Transaction and edge case equivalence tests."""

import time

import pytest

from database import db
from models import CID, Server


@pytest.mark.db_equivalence
class TestTransactionEquivalence:
    """Test transaction behavior is equivalent in both database modes."""

    def test_rollback_equivalence(self, memory_db_app, disk_db_app):
        """Rollback behavior is equivalent in both databases."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Add a server
                server = Server(name="rollback-test", definition="original")
                db.session.add(server)
                db.session.commit()

                # Modify and rollback
                server.definition = "modified"
                db.session.rollback()

                # Refresh to get the actual database state
                db.session.refresh(server)
                results[name] = server.definition

        assert results["memory"] == results["disk"] == "original"

    def test_nested_transaction_equivalence(self, memory_db_app, disk_db_app):
        """Nested transaction behavior is equivalent."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Outer transaction
                server1 = Server(name="outer", definition="outer-def")
                db.session.add(server1)

                # Inner savepoint
                with db.session.begin_nested():
                    server2 = Server(name="inner", definition="inner-def")
                    db.session.add(server2)
                    # This commit is to the savepoint

                db.session.commit()

                count = Server.query.count()
                results[name] = count

        assert results["memory"] == results["disk"] == 2


@pytest.mark.db_equivalence
class TestConcurrencyEquivalence:
    """Test concurrent access patterns behave equivalently."""

    def test_isolation_level_equivalence(self, memory_db_app, disk_db_app):
        """Session isolation behaves equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Create initial data
                server = Server(name="isolation-test", definition="initial")
                db.session.add(server)
                db.session.commit()

                # Query and modify
                server1 = Server.query.filter_by(name="isolation-test").first()
                server1.definition = "modified"

                # Query again (should see uncommitted change in same session)
                server2 = Server.query.filter_by(name="isolation-test").first()
                results[name] = server2.definition

        assert results["memory"] == results["disk"] == "modified"


@pytest.mark.db_equivalence
class TestNullHandlingEquivalence:
    """Test NULL value handling is equivalent in both databases."""

    def test_nullable_field_equivalence(self, memory_db_app, disk_db_app):
        """Nullable fields behave equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Server with nullable definition_cid
                server = Server(
                    name="null-test", definition="has null cid", definition_cid=None
                )
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="null-test").first()
                results[name] = retrieved.definition_cid

        assert results["memory"] == results["disk"] is None

    def test_empty_string_vs_null_equivalence(self, memory_db_app, disk_db_app):
        """Empty strings and NULL are handled equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server1 = Server(name="empty", definition="")
                db.session.add(server1)
                db.session.commit()

                s1 = Server.query.filter_by(name="empty").first()
                results[name] = {"empty": s1.definition}

        assert results["memory"] == results["disk"]
        assert results["memory"]["empty"] == ""


@pytest.mark.db_equivalence
class TestSpecialCharacterEquivalence:
    """Test special character handling is equivalent in both databases."""

    def test_unicode_equivalence(self, memory_db_app, disk_db_app):
        """Unicode characters are handled equivalently."""
        unicode_content = "Hello 世界 🌍 Ñoño"

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="unicode-test", definition=unicode_content)
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="unicode-test").first()
                results[name] = retrieved.definition

        assert results["memory"] == results["disk"] == unicode_content

    def test_sql_injection_characters_equivalence(self, memory_db_app, disk_db_app):
        """SQL injection characters are handled equivalently (safely)."""
        dangerous_content = "'; DROP TABLE servers; --"

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="injection-test", definition=dangerous_content)
                db.session.add(server)
                db.session.commit()

                # Table should still exist and data should be stored literally
                count = Server.query.count()
                retrieved = Server.query.filter_by(name="injection-test").first()
                results[name] = {"count": count, "definition": retrieved.definition}

        assert results["memory"] == results["disk"]
        assert results["memory"]["definition"] == dangerous_content


@pytest.mark.db_equivalence
class TestTimestampEquivalence:
    """Test timestamp handling is equivalent in both databases."""

    def test_auto_timestamp_equivalence(self, memory_db_app, disk_db_app):
        """Auto-generated timestamps behave equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="timestamp-test", definition="test")
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="timestamp-test").first()
                results[name] = {"has_created_at": retrieved.created_at is not None}

        # Both should have timestamps
        assert (
            results["memory"]["has_created_at"]
            == results["disk"]["has_created_at"]
            == True
        )

    def test_timestamp_ordering_equivalence(self, memory_db_app, disk_db_app):
        """Timestamp ordering is equivalent in both databases."""
        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Create servers with slight delay
                server1 = Server(name="first", definition="1")
                db.session.add(server1)
                db.session.commit()

                time.sleep(0.01)  # Small delay

                server2 = Server(name="second", definition="2")
                db.session.add(server2)
                db.session.commit()

                # Order by created_at
                ordered = Server.query.order_by(Server.created_at.asc()).all()
                results[name] = [s.name for s in ordered]

        assert results["memory"] == results["disk"]
        assert results["memory"] == ["first", "second"]
