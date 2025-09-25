import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from auth_providers import auth_manager
from models import Alias, User
from alias_routing import (
    _append_query_string,
    _extract_alias_name,
    _is_relative_target,
    is_potential_alias_path,
    try_alias_redirect,
)
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

        auth_manager._active_provider = auth_manager.providers.get('local')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_alias(self, name='latest', target='/target'):
        alias = Alias(name=name, target_path=target, user_id=self.test_user.id)
        db.session.add(alias)
        db.session.commit()
        return alias

    def login(self, user=None):
        if user is None:
            user = self.test_user
        with self.client.session_transaction() as session:
            session['_user_id'] = user.id
            session['_fresh'] = True

    def test_is_potential_alias_path(self):
        routes = get_existing_routes()
        self.assertFalse(is_potential_alias_path('/', routes))
        self.assertTrue(is_potential_alias_path('/latest', routes))
        self.assertTrue(is_potential_alias_path('/latest/abc', routes))
        self.assertFalse(is_potential_alias_path('/servers/history', routes))

    def test_extract_alias_name_invalid_inputs(self):
        self.assertIsNone(_extract_alias_name(''))
        self.assertIsNone(_extract_alias_name('latest'))
        self.assertIsNone(_extract_alias_name('/'))
        self.assertEqual(_extract_alias_name('/path/to/resource'), 'path')

    def test_is_relative_target_filters_disallowed_forms(self):
        self.assertFalse(_is_relative_target(''))
        self.assertFalse(_is_relative_target('//example.com/file'))
        self.assertFalse(_is_relative_target('https://example.com/file'))
        self.assertTrue(_is_relative_target('/local/path'))

    def test_append_query_string_with_empty_query(self):
        self.assertEqual(_append_query_string('/cid123', ''), '/cid123')

    def test_try_alias_redirect_requires_authentication(self):
        self.create_alias()
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=False)):
                result = try_alias_redirect('/latest')
                self.assertIsNone(result)

    def test_try_alias_redirect_requires_alias_name(self):
        with app.test_request_context('/'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                self.assertIsNone(try_alias_redirect('/'))

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

    def test_try_alias_redirect_combines_existing_query_and_fragment(self):
        self.create_alias(target='/cid123?existing=1#files')
        with app.test_request_context('/latest?download=1'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123?existing=1&download=1#files')

    def test_try_alias_redirect_rejects_non_relative_target(self):
        self.create_alias(target='https://example.com/cid123')
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNone(response)

    def test_not_found_handler_uses_alias(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest/anything'):
            with patch('alias_routing.current_user', new=SimpleNamespace(is_authenticated=True, id=self.test_user.id)):
                response = not_found_error(Exception('not found'))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/cid123')

    def test_aliases_route_requires_login(self):
        response = self.client.get('/aliases', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

    def test_aliases_route_lists_aliases(self):
        self.create_alias(name='latest', target='/cid123')
        self.login()

        response = self.client.get('/aliases')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'latest', response.data)
        self.assertIn(b'/cid123', response.data)

    def test_view_alias_page(self):
        self.create_alias(name='docs', target='/cid/docs')
        self.login()

        response = self.client.get('/aliases/docs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/cid/docs', response.data)

    def test_create_alias_via_form(self):
        self.login()

        response = self.client.post(
            '/aliases/new',
            data={'name': 'release', 'target_path': '/cid456'},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/aliases', response.location)

        created = Alias.query.filter_by(user_id=self.test_user.id, name='release').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.target_path, '/cid456')

    def test_create_alias_rejects_conflicting_route(self):
        self.login()

        response = self.client.post(
            '/aliases/new',
            data={'name': 'servers', 'target_path': '/cid789'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        self.assertIsNone(Alias.query.filter_by(user_id=self.test_user.id, name='servers').first())

    def test_edit_alias_updates_record(self):
        alias = self.create_alias(name='latest', target='/cid123')
        self.login()

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={'name': 'docs', 'target_path': '/docs'},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/aliases/docs', response.location)

        updated = Alias.query.filter_by(user_id=self.test_user.id, name='docs').first()
        self.assertIsNotNone(updated)
        self.assertEqual(updated.target_path, '/docs')

    def test_edit_alias_rejects_conflicting_route_name(self):
        alias = self.create_alias(name='latest', target='/cid123')
        self.login()

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={'name': 'servers', 'target_path': '/cid456'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        persisted = db.session.get(Alias, alias.id)
        self.assertEqual(persisted.name, 'latest')
        self.assertEqual(persisted.target_path, '/cid123')


if __name__ == '__main__':
    unittest.main()
