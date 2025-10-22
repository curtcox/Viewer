"""
Test cases for model methods, particularly focusing on datetime-related functionality.
"""
import os
import unittest
from datetime import datetime, timedelta, timezone

# Set up test environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from identity import ExternalUser
from models import db, CID, PageView, Server, Variable, Secret


class TestModels(unittest.TestCase):
    """Test model methods and properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_has_access_with_valid_payment(self):
        """Test User.has_access() with valid payment."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        user = ExternalUser(
            id='test_user_1',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=future_date,
        )

        self.assertTrue(user.has_access())

    def test_user_has_access_with_expired_payment(self):
        """Test User.has_access() with expired payment."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        user = ExternalUser(
            id='test_user_2',
            email='test2@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=past_date,
        )

        self.assertFalse(user.has_access())

    def test_user_has_access_no_payment_expiry(self):
        """Test User.has_access() with no payment expiry (lifetime access)."""
        user = ExternalUser(
            id='test_user_3',
            email='test3@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=None,
        )

        self.assertTrue(user.has_access())

    def test_user_has_access_not_paid(self):
        """Test User.has_access() when user is not paid."""
        user = ExternalUser(
            id='test_user_4',
            email='test4@example.com',
            first_name='Test',
            last_name='User',
            is_paid=False,
            current_terms_accepted=True,
            payment_expires_at=None,
        )

        self.assertFalse(user.has_access())

    def test_user_has_access_terms_not_accepted(self):
        """Test User.has_access() when terms not accepted."""
        user = ExternalUser(
            id='test_user_5',
            email='test5@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=False,
            payment_expires_at=None,
        )

        self.assertFalse(user.has_access())

    def test_datetime_defaults_on_model_creation(self):
        """Test that datetime defaults are set correctly when creating model instances."""
        test_user_id = 'test_user_datetime'

        # Test CID model datetime defaults
        cid = CID(
            path='/test/path/datetime',
            file_data=b'test content',
            file_size=12,
            uploaded_by_user_id=test_user_id
        )
        db.session.add(cid)
        db.session.commit()

        self.assertIsNotNone(cid.created_at)
        self.assertIsInstance(cid.created_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff_created = datetime.now(timezone.utc).replace(tzinfo=None) - cid.created_at
        self.assertLess(time_diff_created.total_seconds(), 60)

        # Test PageView model datetime defaults
        page_view = PageView(
            user_id=test_user_id,
            path='/test',
            method='GET'
        )
        db.session.add(page_view)
        db.session.commit()

        self.assertIsNotNone(page_view.viewed_at)
        self.assertIsInstance(page_view.viewed_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - page_view.viewed_at
        self.assertLess(time_diff.total_seconds(), 60)

        # Test Server model datetime defaults
        server = Server(
            name='test_server_datetime',
            definition='test definition',
            user_id=test_user_id
        )
        db.session.add(server)
        db.session.commit()

        self.assertIsNotNone(server.created_at)
        self.assertIsNotNone(server.updated_at)
        self.assertIsInstance(server.created_at, datetime)
        self.assertIsInstance(server.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = datetime.now(timezone.utc).replace(tzinfo=None) - server.created_at
        time_diff_updated = datetime.now(timezone.utc).replace(tzinfo=None) - server.updated_at
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

        # Test Variable model datetime defaults
        variable = Variable(
            name='test_var_datetime',
            definition='test value',
            user_id=test_user_id
        )
        db.session.add(variable)
        db.session.commit()

        self.assertIsNotNone(variable.created_at)
        self.assertIsNotNone(variable.updated_at)
        self.assertIsInstance(variable.created_at, datetime)
        self.assertIsInstance(variable.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = datetime.now(timezone.utc).replace(tzinfo=None) - variable.created_at
        time_diff_updated = datetime.now(timezone.utc).replace(tzinfo=None) - variable.updated_at
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

        # Test Secret model datetime defaults
        secret = Secret(
            name='test_secret_datetime',
            definition='test secret value',
            user_id=test_user_id
        )
        db.session.add(secret)
        db.session.commit()

        self.assertIsNotNone(secret.created_at)
        self.assertIsNotNone(secret.updated_at)
        self.assertIsInstance(secret.created_at, datetime)
        self.assertIsInstance(secret.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = datetime.now(timezone.utc).replace(tzinfo=None) - secret.created_at
        time_diff_updated = datetime.now(timezone.utc).replace(tzinfo=None) - secret.updated_at
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

    def test_datetime_onupdate_functionality(self):
        """Test that onupdate datetime fields work correctly."""
        test_user_id = 'test_user_onupdate'

        # Test Server model onupdate functionality
        server = Server(
            name='test_server_onupdate',
            definition='initial definition',
            user_id=test_user_id
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
        server.definition = 'updated definition'
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(server.created_at, initial_created_at)
        self.assertGreater(server.updated_at, initial_updated_at)

        # Test Variable model onupdate functionality
        variable = Variable(
            name='test_var_onupdate',
            definition='initial value',
            user_id=test_user_id
        )
        db.session.add(variable)
        db.session.commit()

        # Store initial timestamps
        initial_var_created_at = variable.created_at
        initial_var_updated_at = variable.updated_at

        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)

        # Update the variable
        variable.definition = 'updated value'
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(variable.created_at, initial_var_created_at)
        self.assertGreater(variable.updated_at, initial_var_updated_at)

        # Test Secret model onupdate functionality
        secret = Secret(
            name='test_secret_onupdate',
            definition='initial secret',
            user_id=test_user_id
        )
        db.session.add(secret)
        db.session.commit()

        # Store initial timestamps
        initial_secret_created_at = secret.created_at
        initial_secret_updated_at = secret.updated_at

        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)

        # Update the secret
        secret.definition = 'updated secret'
        db.session.commit()

        # Verify that created_at didn't change but updated_at did
        self.assertEqual(secret.created_at, initial_secret_created_at)
        self.assertGreater(secret.updated_at, initial_secret_updated_at)


if __name__ == '__main__':
    unittest.main()
