import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from models import Alias, User
from alias_routing import is_potential_alias_path, try_alias_redirect
from routes.core import get_existing_routes, not_found_error


class TestAliasRouting(unittest.TestCase):
    """Tests for alias matching and redirect behaviour."""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.test_user = User(
            id='alias-user',
            email='alias@example.com',
            is_paid=True,
            current_terms_accepted=True,
        )
        db.session.add(self.test_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_alias(self, name='latest', target='/target'):
        alias = Alias(name=name, target_path=target, user_id=self.test_user.id)
        db.session.add(alias)
        db.session.commit()
        return alias

    def test_is_potential_alias_path(self):
        routes = get_existing_routes()
        self.assertFalse(is_potential_alias_path('/', routes))
        self.assertTrue(is_potential_alias_path('/latest', routes))
        self.assertTrue(is_potential_alias_path('/latest/abc', routes))
        self.assertFalse(is_potential_alias_path('/servers/history', routes))

    def test_try_alias_redirect_requires_authentication(self):
        self.create_alias()
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=False)):
                result = try_alias_redirect('/latest')
                self.assertIsNone(result)

    def test_try_alias_redirect_success(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_preserves_query(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest?download=1&format=html'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123?download=1&format=html')

    def test_not_found_handler_uses_alias(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest/anything'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = not_found_error(Exception('not found'))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/cid123')


if __name__ == '__main__':
    unittest.main()
