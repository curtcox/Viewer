"""Tests for literal CID storage behavior.

Literal CIDs (content <= 64 bytes) should NOT be stored in the database
because their content is already embedded in the CID itself.
"""

import unittest

from app import create_app, db
from cid_core import DIRECT_CONTENT_EMBED_LIMIT, generate_cid, is_literal_cid
from cid_storage import ensure_cid_exists, store_cid_from_bytes
from db_access import get_cid_by_path
from models import CID


class TestLiteralCIDStorage(unittest.TestCase):
    """Tests for literal CID storage behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_literal_cid_not_stored_in_database(self):
        """Literal CIDs should not be stored in the database."""
        content = b"small content"
        cid_value = generate_cid(content)

        # Verify it's a literal CID
        self.assertTrue(is_literal_cid(cid_value))

        # Store the CID
        store_cid_from_bytes(content)

        # Verify no database record was created
        db_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNone(db_record)

    def test_literal_cid_resolves_correctly(self):
        """Literal CIDs should resolve correctly without database storage."""
        content = b"hello world"
        cid_value = generate_cid(content)

        # Store the CID (should not actually store in DB)
        store_cid_from_bytes(content)

        # But it should still resolve via get_cid_by_path
        record = get_cid_by_path(f"/{cid_value}")
        self.assertIsNotNone(record)
        self.assertEqual(record.file_data, content)

    def test_hash_based_cid_stored_in_database(self):
        """Hash-based CIDs (> 64 bytes) should be stored in the database."""
        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 10)
        cid_value = generate_cid(content)

        # Verify it's NOT a literal CID
        self.assertFalse(is_literal_cid(cid_value))

        # Store the CID
        store_cid_from_bytes(content)

        # Verify database record was created
        db_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.file_data, content)

    def test_ensure_cid_exists_skips_literal_cids(self):
        """ensure_cid_exists should skip literal CIDs."""
        content = b"literal content"
        cid_value = generate_cid(content)

        # Call ensure_cid_exists
        ensure_cid_exists(cid_value, content)

        # Verify no database record was created
        db_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNone(db_record)

    def test_boundary_cid_not_stored(self):
        """Content exactly at 64 bytes should not be stored."""
        content = b"x" * DIRECT_CONTENT_EMBED_LIMIT
        cid_value = generate_cid(content)

        # Verify it's a literal CID (at boundary)
        self.assertTrue(is_literal_cid(cid_value))

        # Store the CID
        store_cid_from_bytes(content)

        # Verify no database record was created
        db_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNone(db_record)

        # But it should resolve correctly
        record = get_cid_by_path(f"/{cid_value}")
        self.assertIsNotNone(record)
        self.assertEqual(record.file_data, content)

    def test_just_above_boundary_is_stored(self):
        """Content at 65 bytes should be stored in database."""
        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1)
        cid_value = generate_cid(content)

        # Verify it's NOT a literal CID
        self.assertFalse(is_literal_cid(cid_value))

        # Store the CID
        store_cid_from_bytes(content)

        # Verify database record was created
        db_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNotNone(db_record)


class TestLiteralCIDResolution(unittest.TestCase):
    """Tests for literal CID resolution via get_cid_by_path."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_literal_cid_resolved_without_database(self):
        """Literal CIDs should resolve without any database query."""
        content = b"test content"
        cid_value = generate_cid(content)

        # Don't store anything - just try to resolve
        record = get_cid_by_path(f"/{cid_value}")

        # Should resolve correctly
        self.assertIsNotNone(record)
        self.assertEqual(record.file_data, content)
        self.assertEqual(record.file_size, len(content))
        self.assertEqual(record.path, f"/{cid_value}")

    def test_hash_cid_not_resolved_without_database(self):
        """Hash-based CIDs should NOT resolve without database storage."""
        content = b"x" * 100
        cid_value = generate_cid(content)

        # Don't store anything - try to resolve
        record = get_cid_by_path(f"/{cid_value}")

        # Should return None (not in database)
        self.assertIsNone(record)

    def test_literal_cid_record_has_correct_attributes(self):
        """Literal CID records should have all expected attributes."""
        content = b"hello"
        cid_value = generate_cid(content)

        record = get_cid_by_path(f"/{cid_value}")

        # Check all required attributes exist
        self.assertIsNotNone(record.path)
        self.assertIsNotNone(record.file_data)
        self.assertIsNotNone(record.file_size)
        self.assertIsNotNone(record.created_at)


if __name__ == "__main__":
    unittest.main()
