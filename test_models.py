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
from models import db, User, Invitation


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
        user = User(
            id='test_user_1',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=future_date
        )
        db.session.add(user)
        db.session.commit()

        self.assertTrue(user.has_access())

    def test_user_has_access_with_expired_payment(self):
        """Test User.has_access() with expired payment."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        user = User(
            id='test_user_2',
            email='test2@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=past_date
        )
        db.session.add(user)
        db.session.commit()

        self.assertFalse(user.has_access())

    def test_user_has_access_no_payment_expiry(self):
        """Test User.has_access() with no payment expiry (lifetime access)."""
        user = User(
            id='test_user_3',
            email='test3@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=None
        )
        db.session.add(user)
        db.session.commit()

        self.assertTrue(user.has_access())

    def test_user_has_access_not_paid(self):
        """Test User.has_access() when user is not paid."""
        user = User(
            id='test_user_4',
            email='test4@example.com',
            first_name='Test',
            last_name='User',
            is_paid=False,
            current_terms_accepted=True,
            payment_expires_at=None
        )
        db.session.add(user)
        db.session.commit()

        self.assertFalse(user.has_access())

    def test_user_has_access_terms_not_accepted(self):
        """Test User.has_access() when terms not accepted."""
        user = User(
            id='test_user_5',
            email='test5@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=False,
            payment_expires_at=None
        )
        db.session.add(user)
        db.session.commit()

        self.assertFalse(user.has_access())

    def test_invitation_is_valid_pending(self):
        """Test Invitation.is_valid() for pending invitation."""
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = Invitation(
            invitation_code='TEST123',
            inviter_user_id=1,
            status='pending',
            expires_at=future_date
        )
        db.session.add(invitation)
        db.session.commit()

        self.assertTrue(invitation.is_valid())

    def test_invitation_is_valid_expired(self):
        """Test Invitation.is_valid() for expired invitation."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        invitation = Invitation(
            invitation_code='TEST123',
            inviter_user_id=1,
            status='pending',
            expires_at=past_date
        )
        db.session.add(invitation)
        db.session.commit()

        self.assertFalse(invitation.is_valid())

    def test_invitation_is_valid_used(self):
        """Test Invitation.is_valid() for used invitation."""
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = Invitation(
            invitation_code='TEST123',
            inviter_user_id=1,
            status='used',
            expires_at=future_date
        )
        db.session.add(invitation)
        db.session.commit()

        self.assertFalse(invitation.is_valid())

    def test_invitation_is_valid_no_expiry(self):
        """Test Invitation.is_valid() with no expiry date."""
        invitation = Invitation(
            invitation_code='TEST123',
            inviter_user_id=1,
            status='pending',
            expires_at=None
        )
        db.session.add(invitation)
        db.session.commit()

        self.assertTrue(invitation.is_valid())

    def test_invitation_mark_used(self):
        """Test Invitation.mark_used() method."""
        invitation = Invitation(
            invitation_code='TEST123',
            inviter_user_id=1,
            status='pending',
            expires_at=None
        )
        db.session.add(invitation)
        db.session.commit()

        # Create a user to mark as using the invitation
        user = User(
            id='test_user_6',
            email='test6@example.com',
            first_name='Test',
            last_name='User'
        )
        db.session.add(user)
        db.session.commit()

        # Mark invitation as used
        invitation.mark_used(user.id)
        db.session.commit()

        self.assertEqual(invitation.status, 'used')
        self.assertEqual(invitation.used_by_user_id, user.id)
        self.assertIsNotNone(invitation.used_at)
        self.assertIsInstance(invitation.used_at, datetime)

    def test_datetime_defaults_on_model_creation(self):
        """Test that datetime defaults are set correctly when creating model instances."""
        from models import Payment, TermsAcceptance, CID, PageView, Server, Variable, Secret

        # Test Payment model datetime defaults
        payment = Payment(
            user_id='test_user',
            amount=10.0,
            plan_type='annual'
        )
        db.session.add(payment)
        db.session.commit()

        self.assertIsNotNone(payment.payment_date)
        self.assertIsInstance(payment.payment_date, datetime)
        # Note: SQLite stores datetimes as naive, but they represent UTC time
        # The important thing is that the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - payment.payment_date
        self.assertLess(time_diff.total_seconds(), 60)

        # Test TermsAcceptance model datetime defaults
        terms = TermsAcceptance(
            user_id='test_user',
            terms_version='1.0'
        )
        db.session.add(terms)
        db.session.commit()

        self.assertIsNotNone(terms.accepted_at)
        self.assertIsInstance(terms.accepted_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - terms.accepted_at
        self.assertLess(time_diff.total_seconds(), 60)

        # Test Invitation model datetime defaults
        invitation = Invitation(
            invitation_code='TEST456',
            inviter_user_id='test_user'
        )
        db.session.add(invitation)
        db.session.commit()

        self.assertIsNotNone(invitation.created_at)
        self.assertIsInstance(invitation.created_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - invitation.created_at
        self.assertLess(time_diff.total_seconds(), 60)

        # Test CID model datetime defaults
        cid = CID(
            path='/test/path',
            content='test content'
        )
        db.session.add(cid)
        db.session.commit()

        self.assertIsNotNone(cid.created_at)
        self.assertIsNotNone(cid.updated_at)
        self.assertIsInstance(cid.created_at, datetime)
        self.assertIsInstance(cid.updated_at, datetime)
        # Verify the datetimes are recent (within last minute)
        time_diff_created = datetime.now(timezone.utc).replace(tzinfo=None) - cid.created_at
        time_diff_updated = datetime.now(timezone.utc).replace(tzinfo=None) - cid.updated_at
        self.assertLess(time_diff_created.total_seconds(), 60)
        self.assertLess(time_diff_updated.total_seconds(), 60)

        # Test PageView model datetime defaults
        page_view = PageView(
            user_id='test_user',
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
            name='test_server',
            definition='test definition',
            user_id='test_user'
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
            name='test_var',
            definition='test value',
            user_id='test_user'
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
            name='test_secret',
            definition='test secret value',
            user_id='test_user'
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
        from models import CID, Server

        # Test CID model onupdate
        cid = CID(
            path='/test/update/path',
            content='original content'
        )
        db.session.add(cid)
        db.session.commit()

        original_updated_at = cid.updated_at

        # Update the cid
        cid.content = 'updated content'
        db.session.commit()

        # Verify updated_at changed
        self.assertNotEqual(cid.updated_at, original_updated_at)
        self.assertIsInstance(cid.updated_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - cid.updated_at
        self.assertLess(time_diff.total_seconds(), 60)

        # Test Server model onupdate
        server = Server(
            name='test_server_update',
            definition='original definition',
            user_id='test_user'
        )
        db.session.add(server)
        db.session.commit()

        original_updated_at = server.updated_at

        # Update the server
        server.definition = 'updated definition'
        db.session.commit()

        # Verify updated_at changed
        self.assertNotEqual(server.updated_at, original_updated_at)
        self.assertIsInstance(server.updated_at, datetime)
        # Verify the datetime is recent (within last minute)
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - server.updated_at
        self.assertLess(time_diff.total_seconds(), 60)


if __name__ == '__main__':
    unittest.main()
