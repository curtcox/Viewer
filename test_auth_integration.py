#!/usr/bin/env python3
"""
Integration tests for the complete authentication system.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, url_for
from app import app, db
from auth_providers import auth_manager
from models import User, Invitation


class TestAuthIntegration(unittest.TestCase):
    """Integration tests for the complete authentication system."""

    def setUp(self):
        """Set up test environment."""
        # Use the actual app but with test database
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

    def test_auth_manager_detection_local(self):
        """Test that auth manager detects local environment correctly."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            auth_manager._active_provider = None

            provider = auth_manager.get_active_provider()
            self.assertIsNotNone(provider)
            self.assertEqual(provider.get_provider_name(), "Local Development")
            self.assertTrue(auth_manager.is_authentication_available())

    def test_auth_manager_detection_replit(self):
        """Test that auth manager detects Replit environment correctly."""
        with patch.dict(os.environ, {'REPL_ID': 'test-repl-id'}):
            # Reset the active provider
            auth_manager._active_provider = None

            with patch('auth_providers.ReplitAuthProvider.is_available', return_value=True):
                provider = auth_manager.get_active_provider()
                self.assertIsNotNone(provider)
                self.assertEqual(provider.get_provider_name(), "Replit")
                self.assertTrue(auth_manager.is_authentication_available())

    def test_local_auth_flow(self):
        """Test complete local authentication flow."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            auth_manager._active_provider = None

            with self.app.test_client() as client:
                # Test that login URL is correct
                with self.app.app_context():
                    login_url = auth_manager.get_login_url()
                    self.assertEqual(login_url, '/auth/login')

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
                self.assertEqual(response.status_code, 302)  # Redirects to content
                self.assertIn('/content', response.location)

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

                # Try to access protected route after logout
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/auth/login', response.location)

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

    def test_template_integration(self):
        """Test that templates use the correct authentication URLs."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the active provider
            auth_manager._active_provider = None

            with self.app.test_client() as client:
                # Test home page
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'/auth/login', response.data)

                # Test that login button points to correct URL
                self.assertIn(b'href="/auth/login"', response.data)


class TestAuthProviderSwitching(unittest.TestCase):
    """Test switching between authentication providers."""

    def setUp(self):
        """Set up test environment."""
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

    def test_switch_from_local_to_replit(self):
        """Test switching from local to Replit authentication."""
        # Start with local auth
        with patch.dict(os.environ, {}, clear=True):
            auth_manager._active_provider = None
            provider = auth_manager.get_active_provider()
            self.assertEqual(provider.get_provider_name(), "Local Development")

        # Switch to Replit auth
        with patch.dict(os.environ, {'REPL_ID': 'test-repl-id'}):
            auth_manager._active_provider = None
            with patch('auth_providers.ReplitAuthProvider.is_available', return_value=True):
                provider = auth_manager.get_active_provider()
                self.assertEqual(provider.get_provider_name(), "Replit")

    def test_switch_from_replit_to_local(self):
        """Test switching from Replit to local authentication."""
        # Start with Replit auth
        with patch.dict(os.environ, {'REPL_ID': 'test-repl-id'}):
            auth_manager._active_provider = None
            with patch('auth_providers.ReplitAuthProvider.is_available', return_value=True):
                provider = auth_manager.get_active_provider()
                self.assertEqual(provider.get_provider_name(), "Replit")

        # Switch to local auth
        with patch.dict(os.environ, {}, clear=True):
            auth_manager._active_provider = None
            provider = auth_manager.get_active_provider()
            self.assertEqual(provider.get_provider_name(), "Local Development")


class TestAuthErrorHandling(unittest.TestCase):
    """Test error handling in authentication system."""

    def setUp(self):
        """Set up test environment."""
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

    def test_auth_manager_no_providers_available(self):
        """Test auth manager when no providers are available."""
        with patch.dict(os.environ, {}, clear=True):
            auth_manager._active_provider = None

            # Mock both providers to be unavailable
            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=False):
                with patch.object(auth_manager.providers['local'], 'is_available', return_value=False):
                    provider = auth_manager.get_active_provider()
                    self.assertIsNone(provider)
                    self.assertFalse(auth_manager.is_authentication_available())
                    self.assertEqual(auth_manager.get_provider_name(), "None")

    def test_invalid_login_url_when_no_provider(self):
        """Test that login URL handling works when no provider is available."""
        with patch.dict(os.environ, {}, clear=True):
            auth_manager._active_provider = None

            with patch.object(auth_manager.providers['replit'], 'is_available', return_value=False):
                with patch.object(auth_manager.providers['local'], 'is_available', return_value=False):
                    # This should not crash, but return a fallback URL
                    login_url = auth_manager.get_login_url()
                    self.assertEqual(login_url, '/')


if __name__ == '__main__':
    unittest.main()
