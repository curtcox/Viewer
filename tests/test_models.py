"""
Test cases for model methods, particularly focusing on datetime-related functionality.
"""

import os
import unittest
from datetime import datetime, timezone

# Set up test environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-secret-key"
os.environ["TESTING"] = "True"

from app import app
from models import CID, PageView, Secret, Server, Variable, db


class TestModels(unittest.TestCase):
    """Test model methods and properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_datetime_defaults_on_model_creation(self):
        """Test that datetime defaults are set correctly when creating model instances."""
        # Test CID model datetime defaults
        cid = CID(
            path="/test/path/datetime",
            file_data=b"test content",
            file_size=12,
        )
        db.session.add(cid)
        db.session.commit()

        self.assertIsNotNone(cid.created_at)
        self.assertIsInstance(cid.created_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff_created = (
            datetime.now(timezone.utc).replace(tzinfo=None) - cid.created_at
        )
        self.assertLess(time_diff_created.total_seconds(), 60)

        # Test PageView model datetime defaults
        page_view = PageView(path="/test", method="GET")
        db.session.add(page_view)
        db.session.commit()

        self.assertIsNotNone(page_view.viewed_at)
        self.assertIsInstance(page_view.viewed_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = (
            datetime.now(timezone.utc).replace(tzinfo=None) - page_view.viewed_at
        )
        self.assertLess(time_diff.total_seconds(), 60)

        # Test Server model datetime defaults
        server = Server(
            name="test_server_datetime",
            definition="test definition",
        )
        db.session.add(server)
        db.session.commit()

        self.assertIsNotNone(server.created_at)
        self.assertIsNotNone(server.updated_at)
        self.assertIsInstance(server.created_at, datetime)
        self.assertIsInstance(server.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = (
            datetime.now(timezone.utc).replace(tzinfo=None) - server.created_at
        )
        time_diff_updated = (
            datetime.now(timezone.utc).replace(tzinfo=None) - server.updated_at
        )
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

        # Test Variable model datetime defaults
        variable = Variable(
            name="test_var_datetime",
            definition="test value",
        )
        db.session.add(variable)
        db.session.commit()

        self.assertIsNotNone(variable.created_at)
        self.assertIsNotNone(variable.updated_at)
        self.assertIsInstance(variable.created_at, datetime)
        self.assertIsInstance(variable.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = (
            datetime.now(timezone.utc).replace(tzinfo=None) - variable.created_at
        )
        time_diff_updated = (
            datetime.now(timezone.utc).replace(tzinfo=None) - variable.updated_at
        )
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

        # Test Secret model datetime defaults
        secret = Secret(
            name="test_secret_datetime",
            definition="test secret value",
        )
        db.session.add(secret)
        db.session.commit()

        self.assertIsNotNone(secret.created_at)
        self.assertIsNotNone(secret.updated_at)
        self.assertIsInstance(secret.created_at, datetime)
        self.assertIsInstance(secret.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = (
            datetime.now(timezone.utc).replace(tzinfo=None) - secret.created_at
        )
        time_diff_updated = (
            datetime.now(timezone.utc).replace(tzinfo=None) - secret.updated_at
        )
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

    def test_datetime_onupdate_functionality(self):
        """Test that onupdate datetime fields work correctly."""
        # Test Server model onupdate functionality
        server = Server(
            name="test_server_onupdate",
            definition="initial definition",
        )
        db.session.add(server)
        db.session.commit()

        # Store initial timestamps
        initial_created_at = server.created_at
        initial_updated_at = server.updated_at

        # Wait a small amount to ensure timestamp difference
        import time

        time.sleep(0.1)

        # Update the server
        server.definition = "updated definition"
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(server.created_at, initial_created_at)
        self.assertGreater(server.updated_at, initial_updated_at)

        # Test Variable model onupdate functionality
        variable = Variable(
            name="test_var_onupdate",
            definition="initial value",
        )
        db.session.add(variable)
        db.session.commit()

        # Store initial timestamps
        initial_var_created_at = variable.created_at
        initial_var_updated_at = variable.updated_at

        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)

        # Update the variable
        variable.definition = "updated value"
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(variable.created_at, initial_var_created_at)
        self.assertGreater(variable.updated_at, initial_var_updated_at)

        # Test Secret model onupdate functionality
        secret = Secret(
            name="test_secret_onupdate",
            definition="initial secret",
        )
        db.session.add(secret)
        db.session.commit()

        # Store initial timestamps
        initial_secret_created_at = secret.created_at
        initial_secret_updated_at = secret.updated_at

        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)

        # Update the secret
        secret.definition = "updated secret"
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(secret.created_at, initial_secret_created_at)
        self.assertGreater(secret.updated_at, initial_secret_updated_at)


if __name__ == "__main__":
    unittest.main()
