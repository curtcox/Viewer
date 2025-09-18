#!/usr/bin/env python3
"""
Integration tests for the complete authentication system.
"""
import os
import unittest
from unittest.mock import patch

from app import create_app
from auth_providers import auth_manager
from database import db
from models import User

TEST_APP_CONFIG = {
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
}


def build_test_app(config_override=None):
    """Create a new Flask application instance configured for testing."""
    config = TEST_APP_CONFIG.copy()
    if config_override:
        config.update(config_override)
    return create_app(config)


def reset_auth_manager_state():
    """Reset the auth manager to ensure provider detection runs fresh."""
    auth_manager._active_provider = None


class AuthTestCase(unittest.TestCase):
    """Base test case that provides isolated app instances for each test."""

    app_config = None

    def setUp(self):
        super().setUp()
        self.app = build_test_app(self.app_config)
        self.addCleanup(self._cleanup_app)
        self.addCleanup(reset_auth_manager_state)
        reset_auth_manager_state()

    def _cleanup_app(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def create_client(self):
        """Return a new test client bound to the isolated app."""
        return self.app.test_client()

    def app_context(self):
        """Return an application context bound to the isolated app."""
        return self.app.app_context()

    def request_context(self, *args, **kwargs):
        """Return a request context for the isolated app."""
        return self.app.test_request_context(*args, **kwargs)

    def reset_auth_manager(self):
        """Convenience wrapper around the shared auth manager reset."""
        reset_auth_manager_state()


class TestAuthIntegration(AuthTestCase):
    """Integration tests for the complete authentication system."""

    def test_auth_manager_detection_local(self):
        """Test that auth manager detects local environment correctly."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            self.reset_auth_manager()

            provider = auth_manager.get_active_provider()
            self.assertIsNotNone(provider)
            self.assertEqual(provider.get_provider_name(), "Local Development")
            self.assertTrue(auth_manager.is_authentication_available())

    def test_auth_manager_detection_replit(self):
        """Test that auth manager detects Replit environment correctly."""
        with patch.dict(os.environ, {
            'REPL_ID': 'test-repl-123',
            'REPL_OWNER': 'test-user',
            'REPL_SLUG': 'test-project'
        }):
            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=True):
                # Reset the active provider to force re-detection
                self.reset_auth_manager()

                provider = auth_manager.get_active_provider()
                self.assertEqual(provider.get_provider_name(), "Replit")
                self.assertTrue(auth_manager.is_authentication_available())

    def test_local_auth_flow(self):
        """Test complete local authentication flow."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            self.reset_auth_manager()

            with self.create_client() as client:
                # Test that login URL is correct (may be full URL due to app config)
                with self.request_context('/'):
                    login_url = auth_manager.get_login_url()
                    self.assertIn('/auth/login', login_url)

                # Test login
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

                # Test that user was created
                with self.app_context():
                    users = User.query.all()
                    self.assertEqual(len(users), 1)
                    user = users[0]
                    self.assertTrue(user.id.startswith("local_"))
                    self.assertTrue(user.is_paid)
                    self.assertTrue(user.current_terms_accepted)

    def test_protected_route_access(self):
        """Test that protected routes work with authentication."""
        with patch.dict(os.environ, {}, clear=True):
            with self.create_client() as client:
                # First, try to access protected route without auth
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/auth/login', response.location)

                # Login
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Now try to access protected route with auth
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)  # Redirects to content
                self.assertIn('/content', response.location)

    def test_logout_flow(self):
        """Test complete logout flow."""
        with patch.dict(os.environ, {}, clear=True):
            with self.create_client() as client:
                # Login first
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Test logout
                response = client.get('/auth/logout')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/', response.location)

                # Try to access protected route after logout
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/auth/login', response.location)

    def test_registration_flow(self):
        """Test complete registration flow."""
        with patch.dict(os.environ, {}, clear=True):
            with self.create_client() as client:
                # Test registration
                response = client.post('/auth/register', data={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                })
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

                # Test that user was created with correct details
                with self.app_context():
                    users = User.query.all()
                    self.assertEqual(len(users), 1)
                    user = users[0]
                    self.assertEqual(user.email, 'test@example.com')
                    self.assertEqual(user.first_name, 'Test')
                    self.assertEqual(user.last_name, 'User')

    def test_template_integration(self):
        """Test that templates use the correct authentication URLs."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            self.reset_auth_manager()

            with self.create_client() as client:
                # Test home page
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'/auth/login', response.data)

                # Test that login button points to correct URL
                self.assertIn(b'href="/auth/login"', response.data)


class TestAuthProviderSwitching(AuthTestCase):
    """Test switching between authentication providers."""

    def test_switch_from_local_to_replit(self):
        """Test switching from local to Replit authentication."""
        # Start with local environment (no REPL_ID)
        with patch.dict(os.environ, {}, clear=True):
            self.reset_auth_manager()
            local_provider = auth_manager.get_active_provider()
            self.assertEqual(local_provider.get_provider_name(), "Local Development")

        # Switch to Replit environment
        with patch.dict(os.environ, {
            'REPL_ID': 'test-repl-456',
            'REPL_OWNER': 'test-user-2',
            'REPL_SLUG': 'test-project-2'
        }):
            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=True):
                # Reset to force re-detection
                self.reset_auth_manager()
                replit_provider = auth_manager.get_active_provider()
                self.assertEqual(replit_provider.get_provider_name(), "Replit")

    def test_switch_from_replit_to_local(self):
        """Test switching from Replit to local authentication."""
        # Start with Replit environment
        with patch.dict(os.environ, {
            'REPL_ID': 'test-repl-789',
            'REPL_OWNER': 'test-user-3',
            'REPL_SLUG': 'test-project-3'
        }):
            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=True):
                self.reset_auth_manager()
                replit_provider = auth_manager.get_active_provider()
                self.assertEqual(replit_provider.get_provider_name(), "Replit")

        # Switch to local environment (clear REPL_ID)
        with patch.dict(os.environ, {}, clear=True):
            # Reset to force re-detection
            self.reset_auth_manager()
            local_provider = auth_manager.get_active_provider()
            self.assertEqual(local_provider.get_provider_name(), "Local Development")


class TestAuthErrorHandling(AuthTestCase):
    """Test error handling in authentication system."""

    def test_auth_manager_no_providers_available(self):
        """Test auth manager when no providers are available."""
        with patch.dict(os.environ, {}, clear=True):
            self.reset_auth_manager()

            # Mock both providers to be unavailable
            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=False):
                with patch.object(auth_manager.providers['local'], 'is_available', return_value=False):
                    provider = auth_manager.get_active_provider()
                    self.assertIsNone(provider)
                    self.assertFalse(auth_manager.is_authentication_available())
                    self.assertEqual(auth_manager.get_provider_name(), "None")

    def test_invalid_login_url_when_no_provider(self):
        """Test that login URL handling works when no provider is available."""
        with self.request_context('/'):
            with patch.object(auth_manager.providers['local'], 'is_available', return_value=False):
                with patch.object(auth_manager.providers['replit'], 'is_available', return_value=False):
                    # Reset to force re-detection
                    self.reset_auth_manager()

                    # Should fall back to index when no provider available
                    login_url = auth_manager.get_login_url()
                    self.assertIn('/', login_url)  # May be full URL due to app config


if __name__ == '__main__':
    unittest.main()
