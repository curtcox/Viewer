import os
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from alias_definition import format_primary_alias_line
from alias_routing import (
    _append_query_string,
    _extract_alias_name,
    _is_relative_target,
    find_matching_alias,
    is_potential_alias_path,
    try_alias_redirect,
)
from app import app, db
from identity import ensure_default_user
from models import CID, Alias
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
        definition=None,
    ):
        if definition is None:
            pattern_value = pattern
            if match_type == 'literal' and not pattern_value:
                pattern_value = None
            elif pattern_value is None:
                pattern_value = f'/{name}'
            primary_line = format_primary_alias_line(
                match_type,
                pattern_value,
                target,
                ignore_case=ignore_case,
                alias_name=name,
            )
            definition_value = primary_line
        else:
            definition_value = definition

        alias = Alias(
            name=name,
            user_id=self.default_user.id,
            definition=definition_value,
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

    def test_try_alias_redirect_literal_does_not_match_subpath(self):
        self.create_alias(name='docs', target='/documentation', pattern='/docs')
        with app.test_request_context('/docs/anything'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                self.assertIsNone(try_alias_redirect('/docs/anything'))

    def test_try_alias_redirect_glob_pattern(self):
        self.create_alias(name='search', target='/search', match_type='glob', pattern='/search/*')
        with app.test_request_context('/search/documentation'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/search/documentation')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/search')

    def test_try_alias_redirect_prefers_glob_over_literal_for_subpaths(self):
        self.create_alias(name='docs-root', target='/documentation', pattern='/docs')
        self.create_alias(
            name='docs',
            target='/documentation/?q=*',
            match_type='glob',
            pattern='/docs/*',
        )

        with app.test_request_context('/docs/topic'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/topic')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/documentation/?q=topic')

    def test_try_alias_redirect_glob_pattern_expands_wildcard(self):
        self.create_alias(
            name='docs-search',
            target='/documentation/?q=*',
            match_type='glob',
            pattern='/docs/*',
        )
        with app.test_request_context('/docs/api/overview'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/api/overview')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/documentation/?q=api/overview')

    def test_try_alias_redirect_glob_pattern_multiple_wildcards(self):
        self.create_alias(
            name='docs-section',
            target='/archive/*/section/*',
            match_type='glob',
            pattern='/docs/*/pages/*',
        )
        with app.test_request_context('/docs/guides/pages/setup'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/guides/pages/setup')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/archive/guides/section/setup')

    def test_try_alias_redirect_uses_first_matching_declaration(self):
        definition = textwrap.dedent(
            """
            docs/* -> /preferred [glob]
            docs/*/guide -> /special [glob]
            """
        ).strip()

        self.create_alias(
            name='docs',
            target='/preferred',
            match_type='glob',
            pattern='/docs/*',
            definition=definition,
        )

        with app.test_request_context('/docs/topic/guide'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/topic/guide')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/preferred')

    def test_try_alias_redirect_checks_subsequent_declarations(self):
        definition = textwrap.dedent(
            """
            docs/*/guide -> /special [glob]
            docs/* -> /fallback [glob]
            """
        ).strip()

        self.create_alias(
            name='docs',
            target='/special',
            match_type='glob',
            pattern='/docs/*/guide',
            definition=definition,
        )

        with app.test_request_context('/docs/topic/guide'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/topic/guide')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/special')

        with app.test_request_context('/docs/topic/tutorial'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/topic/tutorial')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/fallback')

    def test_try_alias_redirect_glob_pattern_ignore_case(self):
        self.create_alias(
            name='blog',
            target='/posts',
            match_type='glob',
            pattern='/blog-*',
            ignore_case=True,
        )
        with app.test_request_context('/BLOG-today'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/BLOG-today')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/posts')

    def test_try_alias_redirect_regex_pattern(self):
        self.create_alias(name='regex', target='/articles', match_type='regex', pattern=r'^/article/\d+$')
        with app.test_request_context('/article/42'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/article/42')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/articles')

    def test_try_alias_redirect_flask_pattern(self):
        self.create_alias(
            name='profile',
            target='/user-profile/<id>/view',
            match_type='flask',
            pattern='/user/<id>',
        )
        with app.test_request_context('/user/123'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/user/123')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/user-profile/123/view')

    def test_try_alias_redirect_nested_alias_definition(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
              api -> /docs/api/architecture/overview.html
              guide -> /guides/getting-started.html
            """
        ).strip("\n")

        self.create_alias(name='docs', target='/documentation', definition=definition)

        with app.test_request_context('/docs/api'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                match = find_matching_alias('/docs/api')
                self.assertIsNotNone(match)
                self.assertEqual(match.route.alias_path, 'docs/api')
                self.assertEqual(match.route.target_path, '/docs/api/architecture/overview.html')
                response = try_alias_redirect('/docs/api', alias_match=match)
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/docs/api/architecture/overview.html')

        with app.test_request_context('/docs/guide'):
            with patch('alias_routing.current_user', new=SimpleNamespace(id=self.default_user.id)):
                response = try_alias_redirect('/docs/guide')
                self.assertIsNotNone(response)
                self.assertEqual(response.location, '/guides/getting-started.html')

    def test_view_alias_displays_nested_alias_paths(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
              api -> /docs/api/architecture/overview.html
              guide -> /guides/getting-started.html
            """
        ).strip("\n")

        self.create_alias(name='docs', target='/documentation', definition=definition)

        response = self.client.get('/aliases/docs')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('/docs/api/architecture/overview.html', page)
        self.assertIn('badge text-bg-light border">/docs/api<', page)
        self.assertIn('badge text-bg-light border">/docs/guide<', page)

    def test_not_found_handler_uses_alias(self):
        self.create_alias(target='/cid123')
        with app.test_request_context('/latest'):
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

        primary_line = format_primary_alias_line(
            'literal',
            None,
            f'/{cid_value}',
            alias_name='docs',
        )
        definition_text = f"{primary_line}\n# docs definition"

        self.create_alias(
            name='docs',
            target=f'/{cid_value}',
            definition=definition_text,
        )

        response = self.client.get('/aliases/docs')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('Referenced Targets', page)
        self.assertIn(cid_value, page)
        self.assertIn('docs definition', page)
        self.assertIn('Multi-line alias definitions', page)

    def test_create_alias_via_form(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'release',
                'definition': 'release -> /cid456\n# release alias',
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
        self.assertTrue(created.definition.startswith('release -> /cid456'))
        self.assertIn('# release alias', created.definition)

    def test_create_alias_with_glob_match_type(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'release-pattern',
                'definition': 'release-pattern/* -> /cid789 [glob, ignore-case]',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        created = Alias.query.filter_by(user_id=self.default_user.id, name='release-pattern').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.match_type, 'glob')
        self.assertEqual(created.match_pattern, '/release-pattern/*')
        self.assertTrue(created.ignore_case)
        self.assertTrue(created.definition.startswith('/release-pattern/* -> /cid789'))

    def test_new_alias_prefills_name_from_path_query(self):
        response = self.client.get('/aliases/new?path=/docs/latest')

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('value="docs"', page)
        self.assertIn('docs -&gt; /docs/latest', page)

    def test_new_alias_prefills_fields_from_query_parameters(self):
        response = self.client.get('/aliases/new?target_path=%2Fservers%2Fexample&name=example-alias')

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('value="example-alias"', page)
        self.assertIn('example-alias -&gt; /servers/example', page)

    def test_create_alias_rejects_conflicting_route(self):
        response = self.client.post(
            '/aliases/new',
            data={
                'name': 'servers',
                'definition': 'servers -> /cid789',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        self.assertIsNone(Alias.query.filter_by(user_id=self.default_user.id, name='servers').first())

    def test_edit_alias_updates_record(self):
        alias = self.create_alias(name='latest', target='/cid123', definition='# latest version')

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={
                'name': 'docs',
                'definition': 'docs -> /docs\n# docs alias',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/aliases/docs', response.location)

        updated = Alias.query.filter_by(user_id=self.default_user.id, name='docs').first()
        self.assertIsNotNone(updated)
        self.assertEqual(updated.target_path, '/docs')
        self.assertEqual(updated.match_pattern, '/docs')
        self.assertTrue(updated.definition.startswith('docs -> /docs'))
        self.assertIn('# docs alias', updated.definition)

    def test_edit_alias_rejects_conflicting_route_name(self):
        alias = self.create_alias(name='latest', target='/cid123')

        response = self.client.post(
            f'/aliases/{alias.name}/edit',
            data={
                'name': 'servers',
                'definition': 'servers -> /cid456',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'conflicts with an existing route', response.data)
        persisted = db.session.get(Alias, alias.id)
        self.assertEqual(persisted.name, 'latest')
        self.assertEqual(persisted.target_path, '/cid123')

    def test_alias_match_preview_endpoint(self):
        payload = {
            'name': 'docs',
            'definition': 'docs/* -> /docs [glob]',
            'paths': ['/docs/api', '/blog'],
        }

        response = self.client.post('/aliases/match-preview', json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['pattern'], '/docs/*')
        results = {item['value'].strip(): item['matches'] for item in data['results']}
        self.assertTrue(results['/docs/api'])
        self.assertFalse(results['/blog'])

        definition = data.get('definition')
        self.assertIsNotNone(definition)
        self.assertTrue(definition['has_active_paths'])
        self.assertIn('lines', definition)
        primary_line = definition['lines'][0]
        self.assertTrue(primary_line['is_mapping'])
        self.assertFalse(primary_line['has_error'])
        self.assertTrue(primary_line['matches_any'])
        self.assertEqual(primary_line['text'], 'docs/* -> /docs [glob]')

    def test_alias_match_preview_rejects_invalid_pattern(self):
        payload = {
            'name': 'docs',
            'definition': '[ -> /docs [regex]',
            'paths': ['/docs'],
        }

        response = self.client.post('/aliases/match-preview', json=payload)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('Invalid regular expression', data['error'])


if __name__ == '__main__':
    unittest.main()
