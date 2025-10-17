import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from identity import ensure_default_user
from models import Alias, CID
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
        self.default_user = ensure_default_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_alias(
        self,
        name='latest',
        target='/target',
        match_type='literal',
        pattern=None,
        ignore_case=False,
    ):
        alias = Alias(
            name=name,
            target_path=target,
            user_id=self.default_user.id,
            match_type=match_type,
            match_pattern=pattern or f'/{name}',
            ignore_case=ignore_case,
        )
        db.session.add(alias)
        db.session.commit()
        return alias

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

    def test_try_alias_redirect_without_alias_returns_none(self):
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                result = try_alias_redirect('/latest')
                self.assertIsNone(result)

    def test_try_alias_redirect_requires_alias_name(self):
        with app.test_request_context('/'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                self.assertIsNone(try_alias_redirect('/'))

    def test_try_alias_redirect_success(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_preserves_method_for_post(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest', method='POST'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.status_code, 307)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_preserves_query(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest?download=1&format=html'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123?download=1&format=html')

    def test_try_alias_redirect_combines_existing_query_and_fragment(self):
        self.create_alias(target='/cid123?existing=1#files')
        with app.test_request_context('/latest?download=1'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123?existing=1&download=1#files')

    def test_try_alias_redirect_rejects_non_relative_target(self):
        self.create_alias(target='https://example.com/cid123')
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNone(response)

    def test_try_alias_redirect_literal_ignore_case(self):
        self.create_alias(name='Latest', target='/cid123', pattern='/Latest', ignore_case=True)
        with app.test_request_context('/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_glob_pattern(self):
        self.create_alias(name='glob', target='/cid123', match_type='glob', pattern='/release/*/latest')
        with app.test_request_context('/release/v1.2/latest'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/release/v1.2/latest')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_regex_pattern(self):
        self.create_alias(name='regex', target='/cid123', match_type='regex', pattern=r'^/release-\d+$')
        with app.test_request_context('/release-42'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/release-42')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123')

    def test_try_alias_redirect_flask_pattern(self):
        self.create_alias(name='flask', target='/cid123', match_type='flask', pattern='/users/<username>/profile')
        with app.test_request_context('/users/alice/profile'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/users/alice/profile')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/cid123')

    def test_not_found_handler_uses_alias(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest/anything'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = not_found_error(Exception('not found'))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/cid123')

    def login(self):
        """Ensure the default identity exists for compatibility with old helpers."""
        return self.default_user

    def test_aliases_route_lists_aliases_for_default_user(self):
        self.create_alias(name='latest', target='/cid123')

        response = self.client.get('/aliases')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'latest', response.data)
        self.assertIn(b'/cid123', response.data)
        self.assertIn(b'/latest', response.data)

    def test_aliases_route_lists_aliases(self):
        self.create_alias(name='latest', target='/cid123')

        response = self.client.get('/aliases')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'latest', response.data)
        self.assertIn(b'/cid123', response.data)
        self.assertIn(b'/latest', response.data)

    def test_view_alias_page(self):
        cid_value = 'cidtarget123456'
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'document',
            file_size=8,
            uploaded_by_user_id=self.default_user.id,
        )
        db.session.add(cid_record)
        db.session.commit()

        self.create_alias(name='docs', target=f'/{cid_value}')

        response = self.client.get('/aliases/docs')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('Referenced Targets', page)
        self.assertIn(cid_value, page)

    def test_create_alias_via_form(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'release',
                'target_path': '/cid456',
                'match_type': 'literal',
                'match_pattern': '/custom-pattern',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/aliases', response.location)

        created = Alias.query.filter_by(user_id=self.default_user.id, name='release').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.target_path, '/cid456')
        self.assertEqual(created.match_type, 'literal')
        self.assertEqual(created.match_pattern, '/release')
        self.assertFalse(created.ignore_case)

    def test_create_alias_with_glob_match_type(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'release-pattern',
                'target_path': '/cid789',
                'match_type': 'glob',
                'match_pattern': '/release/*/latest',
                'ignore_case': 'y',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        created = Alias.query.filter_by(user_id=self.default_user.id, name='release-pattern').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.match_type, 'glob')
        self.assertEqual(created.match_pattern, '/release/*/latest')
        self.assertTrue(created.ignore_case)

    def test_new_alias_prefills_name_from_path_query(self):
        response = self.client.get('/aliases/new?path=/docs/latest')

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('value="docs"', page)

    def test_create_alias_rejects_conflicting_route(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'servers',
                'target_path': '/cid789',
                'match_type': 'literal',
                'match_pattern': '',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        self.assertIsNone(Alias.query.filter_by(user_id=self.default_user.id, name='servers').first())

    def test_edit_alias_updates_record(self):
        alias = self.create_alias(name='latest', target='/cid123')

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={
                'name': 'docs',
                'target_path': '/docs',
                'match_type': 'literal',
                'match_pattern': '/custom-pattern',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/aliases/docs', response.location)

        updated = Alias.query.filter_by(user_id=self.default_user.id, name='docs').first()
        self.assertIsNotNone(updated)
        self.assertEqual(updated.target_path, '/docs')
        self.assertEqual(updated.match_pattern, '/docs')

    def test_edit_alias_rejects_conflicting_route_name(self):
        alias = self.create_alias(name='latest', target='/cid123')

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={
                'name': 'servers',
                'target_path': '/cid456',
                'match_type': 'literal',
                'match_pattern': '',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        persisted = db.session.get(Alias, alias.id)
        self.assertEqual(persisted.name, 'latest')
        self.assertEqual(persisted.target_path, '/cid123')

    def test_test_pattern_button_displays_results_without_saving(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'preview',
                'target_path': '/cid999',
                'match_type': 'regex',
                'match_pattern': r'^/preview-\d+$',
                'test_strings': '/preview-1\n/preview-x',
                'test_pattern': 'Test Pattern',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Results', response.data)
        self.assertIsNone(Alias.query.filter_by(user_id=self.default_user.id, name='preview').first())


if __name__ == '__main__':
    unittest.main()
