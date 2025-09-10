#!/usr/bin/env python3
"""
Unit tests for the local authentication routes.
"""
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import LoginManager
from app import db
from local_auth import local_auth_bp
from models import User


class TestLocalAuthRoutes(unittest.TestCase):
    """Test the local authentication routes."""

    def setUp(self):
        """Set up test environment."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.config['WTF_CSRF_ENABLED'] = False

        # Initialize Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        login_manager.login_view = 'local_auth.login'

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)

        db.init_app(self.app)

        # Register all necessary routes
        self.app.register_blueprint(local_auth_bp, url_prefix="/auth")

        # Add basic routes that templates need
        @self.app.route('/')
        def index():
            return "Index page"

        @self.app.route('/dashboard')
        def dashboard():
            return "Dashboard page"

        @self.app.route('/plans')
        def plans():
            return "Plans page"

        @self.app.route('/profile')
        def profile():
            return "Profile page"

        @self.app.route('/content')
        def content():
            return "Content page"

        @self.app.route('/terms')
        def terms():
            return "Terms page"

        @self.app.route('/privacy')
        def privacy():
            return "Privacy page"

        with self.app.app_context():
            db.create_all()

    def test_login_get(self):
        """Test GET request to login page."""
        with self.app.test_client() as client:
            response = client.get('/auth/login')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Local Development Login', response.data)
            self.assertIn(b'Login as Local User', response.data)

    def test_login_post(self):
        """Test POST request to login (create and login user)."""
        with self.app.test_client() as client:
            with patch('local_auth.create_local_user') as mock_create_user:
                mock_user = MagicMock()
                mock_user.first_name = "Test"
                mock_create_user.return_value = mock_user

                with patch('local_auth.login_user') as mock_login:
                    response = client.post('/auth/login')

                    self.assertEqual(response.status_code, 302)
                    self.assertIn('/dashboard', response.location)
                    mock_create_user.assert_called_once()
                    mock_login.assert_called_once_with(mock_user)

    def test_login_post_with_next_url(self):
        """Test POST request to login with next URL in session."""
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['next_url'] = '/profile'

            with patch('local_auth.create_local_user') as mock_create_user:
                mock_user = MagicMock()
                mock_create_user.return_value = mock_user

                with patch('local_auth.login_user'):
                    response = client.post('/auth/login')

                    self.assertEqual(response.status_code, 302)
                    self.assertIn('/profile', response.location)

    def test_logout(self):
        """Test logout route."""
        with self.app.test_client() as client:
            with patch('local_auth.logout_user') as mock_logout:
                response = client.get('/auth/logout')

                self.assertEqual(response.status_code, 302)
                self.assertIn('/', response.location)
                mock_logout.assert_called_once()

    def test_register_get(self):
        """Test GET request to registration page."""
        with self.app.test_client() as client:
            response = client.get('/auth/register')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Local Development Registration', response.data)
            self.assertIn(b'Create Local Account', response.data)

    def test_register_post(self):
        """Test POST request to registration."""
        with self.app.test_client() as client:
            with patch('local_auth.create_local_user') as mock_create_user:
                mock_user = MagicMock()
                mock_user.first_name = "Test"
                mock_create_user.return_value = mock_user

                with patch('local_auth.login_user') as mock_login:
                    response = client.post('/auth/register', data={
                        'email': 'test@example.com',
                        'first_name': 'Test',
                        'last_name': 'User'
                    })

                    self.assertEqual(response.status_code, 302)
                    self.assertIn('/dashboard', response.location)
                    mock_create_user.assert_called_once_with(
                        email='test@example.com',
                        first_name='Test',
                        last_name='User'
                    )
                    mock_login.assert_called_once_with(mock_user)

    def test_register_post_empty_fields(self):
        """Test POST request to registration with empty fields."""
        with self.app.test_client() as client:
            with patch('local_auth.create_local_user') as mock_create_user:
                mock_user = MagicMock()
                mock_user.first_name = "Local"
                mock_create_user.return_value = mock_user

                with patch('local_auth.login_user'):
                    response = client.post('/auth/register', data={
                        'email': '',
                        'first_name': '',
                        'last_name': ''
                    })

                    self.assertEqual(response.status_code, 302)
                    mock_create_user.assert_called_once_with(
                        email=None,
                        first_name=None,
                        last_name=None
                    )

    def test_register_post_with_next_url(self):
        """Test POST request to registration with next URL in session."""
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['next_url'] = '/settings'

            with patch('local_auth.create_local_user') as mock_create_user:
                mock_user = MagicMock()
                mock_create_user.return_value = mock_user

                with patch('local_auth.login_user'):
                    response = client.post('/auth/register', data={
                        'email': 'test@example.com',
                        'first_name': 'Test',
                        'last_name': 'User'
                    })

                    self.assertEqual(response.status_code, 302)
                    self.assertIn('/settings', response.location)


class TestLocalAuthIntegration(unittest.TestCase):
    """Integration tests for local authentication."""

    def setUp(self):
        """Set up test environment."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.config['WTF_CSRF_ENABLED'] = False

        # Initialize Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        login_manager.login_view = 'local_auth.login'

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)

        db.init_app(self.app)

        # Register all necessary routes
        self.app.register_blueprint(local_auth_bp, url_prefix="/auth")

        # Add basic routes that templates need
        @self.app.route('/')
        def index():
            return "Index page"

        @self.app.route('/dashboard')
        def dashboard():
            return "Dashboard page"

        @self.app.route('/plans')
        def plans():
            return "Plans page"

        @self.app.route('/profile')
        def profile():
            return "Profile page"

        @self.app.route('/content')
        def content():
            return "Content page"

        @self.app.route('/terms')
        def terms():
            return "Terms page"

        @self.app.route('/privacy')
        def privacy():
            return "Privacy page"

        with self.app.app_context():
            db.create_all()

    def test_full_login_flow(self):
        """Test complete login flow from GET to POST."""
        with self.app.test_client() as client:
            # First, get the login page
            response = client.get('/auth/login')
            self.assertEqual(response.status_code, 200)

            # Then, submit the login form
            response = client.post('/auth/login')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)

            # Check that a user was created in the database
            with self.app.app_context():
                users = User.query.all()
                self.assertEqual(len(users), 1)
                user = users[0]
                self.assertTrue(user.id.startswith("local_"))
                self.assertTrue(user.is_paid)
                self.assertTrue(user.current_terms_accepted)

    def test_full_registration_flow(self):
        """Test complete registration flow."""
        with self.app.test_client() as client:
            # First, get the registration page
            response = client.get('/auth/register')
            self.assertEqual(response.status_code, 200)

            # Then, submit the registration form
            response = client.post('/auth/register', data={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            })
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)

            # Check that a user was created with the correct details
            with self.app.app_context():
                users = User.query.all()
                self.assertEqual(len(users), 1)
                user = users[0]
                self.assertEqual(user.email, 'test@example.com')
                self.assertEqual(user.first_name, 'Test')
                self.assertEqual(user.last_name, 'User')
                self.assertTrue(user.is_paid)
                self.assertTrue(user.current_terms_accepted)

    def test_multiple_logins_create_different_users(self):
        """Test that multiple logins create different users."""
        with self.app.test_client() as client:
            # First login
            response = client.post('/auth/login')
            self.assertEqual(response.status_code, 302)

            # Second login
            response = client.post('/auth/login')
            self.assertEqual(response.status_code, 302)

            # Check that two users were created
            with self.app.app_context():
                users = User.query.all()
                self.assertEqual(len(users), 2)
                self.assertNotEqual(users[0].id, users[1].id)


if __name__ == '__main__':
    unittest.main()
