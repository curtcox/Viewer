#!/usr/bin/env python3
"""
Simple unit tests for the authentication system using the actual app.
"""
import os
import unittest
from unittest.mock import patch
from app import app, db
from auth_providers import auth_manager, create_local_user, save_user_from_claims
from models import User, Invitation


class TestAuthSystemSimple(unittest.TestCase):
    """Simple tests for the authentication system."""

    def setUp(self):
        """Set up test environment."""
        # Use the actual app with test database
        self.app = app
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.drop_all()

    def test_auth_manager_detection(self):
        """Test that auth manager correctly detects the environment."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            auth_manager._active_provider = None

            provider = auth_manager.get_active_provider()
            self.assertIsNotNone(provider)
            self.assertEqual(provider.get_provider_name(), "Local Development")
            self.assertTrue(auth_manager.is_authentication_available())

    def test_create_local_user(self):
        """Test local user creation."""
        with self.app.app_context():
            user = create_local_user(
                email="test@example.com",
                first_name="Test",
                last_name="User"
            )

            self.assertIsInstance(user, User)
            self.assertEqual(user.email, "test@example.com")
            self.assertEqual(user.first_name, "Test")
            self.assertEqual(user.last_name, "User")
            self.assertTrue(user.is_paid)
            self.assertTrue(user.current_terms_accepted)
            self.assertTrue(user.id.startswith("local_"))

    def test_create_local_user_defaults(self):
        """Test local user creation with default values."""
        with self.app.app_context():
            user = create_local_user()

            self.assertIsInstance(user, User)
            self.assertTrue(user.email.startswith("local-user-"))
            self.assertEqual(user.first_name, "Local")
            self.assertEqual(user.last_name, "User")
            self.assertTrue(user.is_paid)
            self.assertTrue(user.current_terms_accepted)

    def test_save_user_from_claims_existing_user(self):
        """Test saving user from claims for existing user."""
        with self.app.app_context():
            # Create existing user
            existing_user = User()
            existing_user.id = "test-user-id"
            existing_user.email = "old@example.com"
            existing_user.first_name = "Old"
            existing_user.last_name = "Name"
            db.session.add(existing_user)
            db.session.commit()

            # Update with new claims
            user_claims = {
                'sub': 'test-user-id',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'Name'
            }

            user = save_user_from_claims(user_claims)

            self.assertEqual(user.id, "test-user-id")
            self.assertEqual(user.email, "new@example.com")
            self.assertEqual(user.first_name, "New")
            self.assertEqual(user.last_name, "Name")

    def test_save_user_from_claims_new_user_with_invitation(self):
        """Test saving new user from claims with valid invitation."""
        with self.app.app_context():
            # Create inviter user
            inviter = User()
            inviter.id = "inviter-id"
            inviter.email = "inviter@example.com"
            db.session.add(inviter)
            db.session.commit()

            # Create invitation
            invitation = Invitation()
            invitation.inviter_user_id = inviter.id
            invitation.invitation_code = "test-code"
            invitation.status = "pending"
            db.session.add(invitation)
            db.session.commit()

            # Create new user with invitation
            user_claims = {
                'sub': 'new-user-id',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User'
            }

            user = save_user_from_claims(user_claims, "test-code")

            self.assertEqual(user.id, "new-user-id")
            self.assertEqual(user.email, "new@example.com")
            self.assertEqual(user.invited_by_user_id, inviter.id)
            self.assertEqual(user.invitation_used_id, invitation.id)

            # Check invitation was marked as used
            db.session.refresh(invitation)
            self.assertEqual(invitation.status, "used")
            self.assertEqual(invitation.used_by_user_id, "new-user-id")

    def test_save_user_from_claims_new_user_no_invitation(self):
        """Test saving new user from claims without invitation."""
        with self.app.app_context():
            user_claims = {
                'sub': 'new-user-id',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User'
            }

            with self.assertRaises(ValueError) as context:
                save_user_from_claims(user_claims)

            self.assertIn("Invitation code required", str(context.exception))

    def test_save_user_from_claims_invalid_invitation(self):
        """Test saving new user from claims with invalid invitation."""
        with self.app.app_context():
            user_claims = {
                'sub': 'new-user-id',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User'
            }

            with self.assertRaises(ValueError) as context:
                save_user_from_claims(user_claims, "invalid-code")

            self.assertIn("Invalid or expired invitation code", str(context.exception))

    def test_local_auth_flow(self):
        """Test complete local authentication flow."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            auth_manager._active_provider = None

            with self.app.test_client() as client:
                # Test login
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

                # Test that user was created
                with self.app.app_context():
                    users = User.query.all()
                    self.assertEqual(len(users), 1)
                    user = users[0]
                    self.assertTrue(user.id.startswith("local_"))
                    self.assertTrue(user.is_paid)
                    self.assertTrue(user.current_terms_accepted)

    def test_registration_flow(self):
        """Test complete registration flow."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Test registration
                response = client.post('/auth/register', data={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                })
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

                # Test that user was created with correct details
                with self.app.app_context():
                    users = User.query.all()
                    self.assertEqual(len(users), 1)
                    user = users[0]
                    self.assertEqual(user.email, 'test@example.com')
                    self.assertEqual(user.first_name, 'Test')
                    self.assertEqual(user.last_name, 'User')

    def test_logout_flow(self):
        """Test complete logout flow."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Login first
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Test logout
                response = client.get('/auth/logout')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/', response.location)

    def test_protected_route_access(self):
        """Test that protected routes work with authentication."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # First, try to access protected route without auth
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/auth/login', response.location)

                # Login
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Now try to access protected route with auth
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)  # Redirects to profile overview
                self.assertIn('/profile', response.location)

    def test_home_page_renders(self):
        """Test that home page renders correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'SecureApp', response.data)
                self.assertIn(b'/auth/login', response.data)

    def test_local_login_page_renders(self):
        """Test that local login page renders correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/auth/login')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Local Development Login', response.data)
                self.assertIn(b'Login as Local User', response.data)

    def test_local_register_page_renders(self):
        """Test that local register page renders correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/auth/register')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Local Development Registration', response.data)
                self.assertIn(b'Create Local Account', response.data)


if __name__ == '__main__':
    unittest.main()
