import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from werkzeug.routing import RequestRedirect

from alias_definition import format_primary_alias_line
from app import app, db
from models import CID, Alias, Server, ServerInvocation


class TestMetaRoute(unittest.TestCase):
    """Tests for the /meta diagnostic route."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_cid(self, cid_value: str, content: bytes = b'test'):
        record = CID(
            path=f'/{cid_value}',
            file_data=content,
            file_size=len(content),
        )
        db.session.add(record)
        db.session.commit()
        return record

    def _create_alias(
        self,
        *,
        name: str = 'docs',
        target: str = '/docs',
        match_type: str = 'literal',
        pattern: str | None = None,
        ignore_case: bool = False,
    ):
        pattern_value = pattern
        if match_type == 'literal' and not pattern_value:
            pattern_value = None
        elif pattern_value is None:
            pattern_value = f'/{name}'
        definition_text = format_primary_alias_line(
            match_type,
            pattern_value,
            target,
            ignore_case=ignore_case,
            alias_name=name,
        )
        alias = Alias(
            name=name,
            definition=definition_text,
        )
        db.session.add(alias)
        db.session.commit()
        return alias

    def _create_server(self, name: str = 'demo-server', definition: str = 'print("hi")'):
        server = Server(name=name, definition=definition)
        db.session.add(server)
        db.session.commit()
        return server

    def test_meta_route_reports_route_information(self):
        with self.app.app_context():
            response = self.client.get('/meta/profile')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['path'], '/profile')
            self.assertEqual(data['status_code'], 200)
            self.assertIn('resolution', data)
            self.assertEqual(data['resolution']['type'], 'route')
            self.assertEqual(data['resolution']['endpoint'], 'main.profile')
            self.assertIn('/source/routes/core.py', data['source_links'])

    def test_meta_route_returns_404_for_unknown_path(self):
        with self.app.app_context():
            response = self.client.get('/meta/does-not-exist')
            self.assertEqual(response.status_code, 404)

            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Path not found')

    def test_meta_route_includes_template_source_links(self):
        with self.app.app_context():
            response = self.client.get('/meta/settings')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertIn('/source/templates/settings.html', data['source_links'])

    def test_meta_route_includes_server_event_links_for_cid(self):
        with self.app.app_context():
            self._create_cid('cid-result', b'result')
            self._create_server(name='demo-server')
            self._create_alias(name='docs', target='/docs')
            record = CID.query.filter_by(path='/cid-result').first()
            record.file_data = b'Check /docs /servers/demo-server /demo-server and /cid-inv'
            db.session.commit()

            related_cids = ['cid-inv', 'cid-request', 'cid-servers', 'cid-vars', 'cid-secrets']
            for cid in related_cids:
                self._create_cid(cid, b'extra')

            invocation = ServerInvocation(
                server_name='demo-server',
                result_cid='cid-result',
                invocation_cid='cid-inv',
                request_details_cid='cid-request',
                servers_cid='cid-servers',
                variables_cid='cid-vars',
                secrets_cid='cid-secrets',
            )
            db.session.add(invocation)
            db.session.commit()

            response = self.client.get('/meta/cid-result')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['resolution']['type'], 'cid')
            self.assertEqual(data['resolution']['cid'], 'cid-result')
            self.assertIn('server_events', data)

            events = data['server_events']
            self.assertTrue(any(event['server_name'] == 'demo-server' for event in events))

            first_event = events[0]
            self.assertIn('/server_events', first_event['event_page'])

            expected_links = {f'/meta/{cid}' for cid in ['cid-result'] + related_cids}
            self.assertTrue(expected_links.issubset(set(first_event['related_cid_meta_links'])))

            self.assertIn('/source/cid_utils.py', data['source_links'])
            self.assertIn('/source/server_execution.py', data['source_links'])
            self.assertIn('referenced_entities', data)
            refs = data['referenced_entities']
            self.assertTrue(any(ref['name'] == 'docs' for ref in refs.get('aliases', [])))
            self.assertTrue(any(ref['name'] == 'demo-server' for ref in refs.get('servers', [])))
            self.assertTrue(any(ref['cid'] == 'cid-inv' for ref in refs.get('cids', [])))

    def test_meta_route_html_format_renders_links(self):
        with self.app.app_context():
            response = self.client.get('/meta/settings.html')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/html')

            body = response.data.decode('utf-8')
            self.assertIn('<a href="/settings"><code>/settings</code></a>', body)
            self.assertIn('<a href="/source/templates/settings.html"><code>/source/templates/settings.html</code></a>', body)

    def test_meta_route_html_includes_related_tests_links(self):
        with self.app.app_context():
            response = self.client.get('/meta/settings.html')
            self.assertEqual(response.status_code, 200)

            body = response.data.decode('utf-8')
            self.assertIn('Related automated coverage', body)
            self.assertIn('/source/templates/settings.html', body)
            self.assertIn('/source/tests/test_routes_comprehensive.py', body)
            self.assertIn('TestSettingsRoutes::test_settings_page', body)

    def test_meta_route_reports_alias_redirect_metadata(self):
        with self.app.app_context():
            self._create_alias(name='shortcut', target='/servers#overview')

            response = self.client.get('/meta/shortcut?source=meta')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 302)
            self.assertEqual(data['resolution']['type'], 'alias_redirect')
            self.assertEqual(data['resolution']['alias'], 'shortcut')
            self.assertTrue(data['resolution']['available'])
            self.assertEqual(data['resolution']['target_path'], '/servers#overview')
            self.assertIn('source=meta', data['resolution']['redirect_location'])
            self.assertIn('target_metadata', data['resolution'])
            target_info = data['resolution']['target_metadata']
            self.assertEqual(target_info['path'], '/servers')
            self.assertTrue(target_info['available'])
            self.assertEqual(target_info['resolution']['type'], 'route')
            self.assertIn('/source/alias_routing.py', data['source_links'])

    def test_meta_route_reports_server_execution_requirements(self):
        with self.app.app_context():
            self._create_server(name='process-data')

            response = self.client.get('/meta/process-data')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 302)
            self.assertEqual(data['resolution']['type'], 'server_execution')
            self.assertEqual(data['resolution']['server_name'], 'process-data')

    def test_meta_route_reports_aliases_targeting_path(self):
        with self.app.app_context():
            self._create_alias(name='docs', target='/settings')
            self._create_alias(name='settings-alias', target='/settings?from=alias')

            response = self.client.get('/meta/settings')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertIn('aliases_targeting_path', data)
            alias_details = data['aliases_targeting_path']
            self.assertIsInstance(alias_details, list)
            alias_names = {entry['name'] for entry in alias_details}
            self.assertIn('docs', alias_names)
            self.assertIn('settings-alias', alias_names)
            for entry in alias_details:
                self.assertIn('meta_link', entry)
                if entry['name'] == 'settings-alias':
                    self.assertEqual(entry['target_path'], '/settings?from=alias')

    def test_meta_route_handles_versioned_server_without_match(self):
        with self.app.app_context():
            self._create_server(name='reporting')

            with patch('routes.servers.get_server_definition_history', return_value=[]):
                response = self.client.get('/meta/reporting/unknown')

            self.assertEqual(response.status_code, 404)
            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 404)
            self.assertFalse(data['resolution']['available'])
            self.assertEqual(data['resolution']['matches'], [])

    def test_meta_route_handles_versioned_server_multiple_matches(self):
        with self.app.app_context():
            self._create_server(name='analytics')

            history = [
                {
                    'definition_cid': 'abc123',
                    'snapshot_cid': 'snap-1',
                    'created_at': datetime(2024, 1, 5, tzinfo=timezone.utc),
                },
                {
                    'definition_cid': 'abc999',
                    'snapshot_cid': 'snap-2',
                    'created_at': None,
                },
            ]

            with patch('routes.servers.get_server_definition_history', return_value=history):
                response = self.client.get('/meta/analytics/abc')

            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 400)
            self.assertFalse(data['resolution']['available'])
            matches = data['resolution']['matches']
            self.assertEqual(len(matches), 2)
            self.assertEqual(matches[0]['definition_cid'], 'abc123')
            self.assertEqual(matches[0]['snapshot_cid'], 'snap-1')
            self.assertIn('T00:00:00+00:00', matches[0]['created_at'])
            self.assertIsNone(matches[1]['created_at'])

    def test_meta_route_handles_versioned_server_single_match(self):
        with self.app.app_context():
            self._create_server(name='pipeline')

            history = [
                {
                    'definition_cid': 'xyz789',
                    'snapshot_cid': 'snap-final',
                    'created_at': datetime(2024, 2, 1, 12, 30, tzinfo=timezone.utc),
                }
            ]

            with patch('routes.servers.get_server_definition_history', return_value=history):
                response = self.client.get('/meta/pipeline/xyz789')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 302)
            self.assertTrue(data['resolution']['available'])
            self.assertEqual(data['resolution']['definition_cid'], 'xyz789')
            self.assertEqual(data['resolution']['snapshot_cid'], 'snap-final')
            self.assertIn('2024-02-01T12:30:00+00:00', data['resolution']['created_at'])

    def test_meta_route_reports_versioned_helper_function_details(self):
        definition = """
 def render_row(label):
     return {"output": label, "content_type": "text/plain"}

 def main(label):
     return render_row(label)
 """

        with self.app.app_context():
            self._create_server(name='pipeline', definition=definition)

            history = [
                {
                    'definition_cid': 'xyz789',
                    'snapshot_cid': 'snap-final',
                    'definition': definition,
                    'created_at': datetime(2024, 2, 1, 12, 30, tzinfo=timezone.utc),
                }
            ]

            with patch('routes.servers.get_server_definition_history', return_value=history):
                response = self.client.get('/meta/pipeline/xyz789/render_row')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 302)
            self.assertTrue(data['resolution']['available'])
            self.assertEqual(data['resolution']['type'], 'versioned_server_function_execution')
            self.assertEqual(data['resolution']['function_name'], 'render_row')
            parameters = data['resolution'].get('function_parameters')
            self.assertIsInstance(parameters, list)
            self.assertEqual(parameters[0]['name'], 'label')

    def test_meta_route_reports_redirect_metadata_for_trailing_slash(self):
        with self.app.app_context():

            class FakeAdapter:
                def match(self, path, method=None, return_rule=False):
                    raise RequestRedirect('http://localhost/settings')

            with patch.object(self.app.url_map, 'bind', return_value=FakeAdapter()):
                response = self.client.get('/meta/needs-redirect')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['resolution']['type'], 'redirect')
            self.assertEqual(data['status_code'], 308)
            self.assertIn('/settings', data['resolution']['location'])

    def test_meta_route_reports_method_not_allowed_metadata(self):
        with self.app.app_context():
            response = self.client.get('/meta/variables/example/delete')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['status_code'], 405)
            self.assertEqual(data['resolution']['type'], 'method_not_allowed')
            self.assertIn('POST', data['resolution']['allowed_methods'])
            self.assertIn('POST', data['resolution']['methods'])
            self.assertIn('/source/routes/meta.py', data['source_links'])

    def test_meta_route_normalizes_blank_requested_path(self):
        with self.app.app_context():
            response = self.client.get('/meta')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['path'], '/')
            self.assertEqual(data['status_code'], 200)


if __name__ == '__main__':
    unittest.main()
