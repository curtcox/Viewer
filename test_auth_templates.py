#!/usr/bin/env python3
"""
Unit tests for authentication template integration.
"""
import os
import unittest
from unittest.mock import patch
from flask import Flask
from app import app, db


class TestAuthTemplateIntegration(unittest.TestCase):
    """Test that templates correctly use the new authentication system."""

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

    def test_index_template_local_auth(self):
        """Test that index template shows local auth when in local environment."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # Check that local auth URLs are used
                self.assertIn(b'/auth/login', response.data)
                self.assertNotIn(b'replit_auth.login', response.data)

                # Check that login buttons are present
                self.assertIn(b'Get Started', response.data)
                self.assertIn(b'Start Free Trial', response.data)

    def test_index_template_replit_auth(self):
        """Test that index template shows Replit auth when in Replit environment."""
        with patch.dict(os.environ, {'REPL_ID': 'test-repl-id'}):
            with patch('auth_providers.ReplitAuthProvider.is_available', return_value=True):
                with self.app.test_client() as client:
                    response = client.get('/')
                    self.assertEqual(response.status_code, 200)

                    # Check that Replit auth URLs are used
                    self.assertIn(b'/auth/login', response.data)  # Still uses /auth/login
                    self.assertNotIn(b'replit_auth.login', response.data)

    def test_base_template_navigation_local_auth(self):
        """Test that base template navigation works with local auth."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # Check navigation login link
                self.assertIn(b'href="/auth/login"', response.data)
                self.assertNotIn(b'replit_auth.login', response.data)

    def test_base_template_logout_link(self):
        """Test that base template logout link works correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # First login to get authenticated state
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Now check that logout link is present
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'/auth/logout', response.data)

    def test_local_login_template_content(self):
        """Test that local login template renders correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/auth/login')
                self.assertEqual(response.status_code, 200)

                # Check template content
                self.assertIn(b'Local Development Login', response.data)
                self.assertIn(b'Login as Local User', response.data)
                self.assertIn(b'Development Mode', response.data)
                self.assertIn(b'Register with Details', response.data)
                self.assertIn(b'/auth/register', response.data)

    def test_local_register_template_content(self):
        """Test that local register template renders correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/auth/register')
                self.assertEqual(response.status_code, 200)

                # Check template content
                self.assertIn(b'Local Development Registration', response.data)
                self.assertIn(b'Create Local Account', response.data)
                self.assertIn(b'Development Mode', response.data)
                self.assertIn(b'Quick Login', response.data)
                self.assertIn(b'/auth/login', response.data)

                # Check form fields
                self.assertIn(b'name="email"', response.data)
                self.assertIn(b'name="first_name"', response.data)
                self.assertIn(b'name="last_name"', response.data)

    def test_template_context_variables(self):
        """Test that template context variables are correctly set."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # The context processor should inject these variables
                # We can't directly test them, but we can test their effects
                # by checking that the template renders without errors
                self.assertNotIn(b'undefined', response.data)
                self.assertNotIn(b'None', response.data)

    def test_template_error_handling(self):
        """Test that templates handle authentication errors gracefully."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Test accessing a protected route without authentication
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 302)

                # Should redirect to login
                self.assertIn('/auth/login', response.location)

    def test_template_authenticated_user_display(self):
        """Test that templates correctly display authenticated user info."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Login first
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)

                # Check that user info is displayed
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # Should show user dropdown (authenticated state)
                self.assertIn(b'dropdown-toggle', response.data)

    def test_template_unauthenticated_user_display(self):
        """Test that templates correctly display unauthenticated user state."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # Should show login link (unauthenticated state)
                self.assertIn(b'Login', response.data)
                self.assertNotIn(b'dropdown-toggle', response.data)


class TestAuthTemplateForms(unittest.TestCase):
    """Test authentication form templates."""

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

    def test_local_login_form_submission(self):
        """Test that local login form can be submitted."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Get the login page
                response = client.get('/auth/login')
                self.assertEqual(response.status_code, 200)

                # Submit the form
                response = client.post('/auth/login')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

    def test_local_register_form_submission(self):
        """Test that local register form can be submitted."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Get the register page
                response = client.get('/auth/register')
                self.assertEqual(response.status_code, 200)

                # Submit the form with data
                response = client.post('/auth/register', data={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                })
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)

    def test_local_register_form_empty_submission(self):
        """Test that local register form can be submitted with empty fields."""
        with patch.dict(os.environ, {}, clear=True):
            with self.app.test_client() as client:
                # Submit the form with empty data
                response = client.post('/auth/register', data={
                    'email': '',
                    'first_name': '',
                    'last_name': ''
                })
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard', response.location)


if __name__ == '__main__':
    unittest.main()
