import json
import platform
import shutil
import sys
import unittest
from contextlib import ExitStack, contextmanager
from html import escape
from pathlib import Path
from unittest.mock import patch

from importlib import metadata

from app import create_app, db
from cid_presenter import format_cid
from cid_utils import generate_cid
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from datetime import datetime, timezone
from alias_definition import format_primary_alias_line
from models import Alias, CID, EntityInteraction, Secret, Server, Variable


class ImportExportRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.user_id = 'user-123'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _login_patch(self, mock_current_user):
        mock_current_user.id = self.user_id
        return mock_current_user

    @contextmanager
    def logged_in(self):
        with ExitStack() as stack:
            route_user = stack.enter_context(patch('routes.import_export.current_user'))
            self._login_patch(route_user)
            yield

    def assert_flash_present(self, message: str, response_data: bytes):
        text = response_data.decode('utf-8')
        html_message = escape(message, quote=True)
        numeric_html_message = message.replace('"', '&#34;')
        self.assertTrue(
            message in text or html_message in text or numeric_html_message in text,
            f'Expected flash message "{message}" in response: {text}',
        )

    def test_export_includes_selected_collections(self):
        with self.app.app_context():
            definition_text = format_primary_alias_line(
                'glob',
                '/demo/*',
                '/demo',
                ignore_case=True,
                alias_name='alias-one',
            )
            definition_text = f"{definition_text}\n# export example"
            alias = Alias(
                name='alias-one',
                user_id=self.user_id,
                definition=definition_text,
            )
            server = Server(name='server-one', definition='print("hi")', user_id=self.user_id)
            variable = Variable(name='var-one', definition='value', user_id=self.user_id)
            secret = Secret(name='secret-one', definition='super-secret', user_id=self.user_id)
            db.session.add_all([alias, server, variable, secret])
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/export', data={
                'include_aliases': 'y',
                'include_servers': 'y',
                'include_variables': 'y',
                'include_secrets': 'y',
                'include_history': 'y',
                'include_cid_map': 'y',
                'secret_key': 'passphrase',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your export is ready', response.data)

        with self.app.app_context():
            cid_records = CID.query.all()
            export_record = next(
                (record for record in cid_records if b'"version"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))
            cid_value = export_record.path.lstrip('/')

        self.assertEqual(payload['version'], 4)
        self.assertIn('generated_at', payload)

        project_files = payload.get('project_files', {})
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)
        for entry in project_files.values():
            self.assertIn('cid', entry)

        aliases = payload.get('aliases', [])
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]['name'], 'alias-one')
        self.assertIn('definition_cid', aliases[0])
        self.assertNotIn('definition', aliases[0])
        alias_definition_cid = aliases[0]['definition_cid']

        servers = payload.get('servers', [])
        self.assertEqual(len(servers), 1)
        self.assertIn('definition_cid', servers[0])
        self.assertNotIn('definition', servers[0])

        cid_values = payload.get('cid_values', {})
        self.assertIn(alias_definition_cid, cid_values)
        self.assertEqual(
            cid_values[alias_definition_cid],
            {'encoding': 'utf-8', 'value': definition_text},
        )
        self.assertIn(servers[0]['definition_cid'], cid_values)
        self.assertEqual(
            cid_values[servers[0]['definition_cid']],
            {'encoding': 'utf-8', 'value': 'print("hi")'},
        )
        for entry in project_files.values():
            self.assertIn(entry['cid'], cid_values)

        variables = payload.get('variables', [])
        self.assertEqual(variables[0]['definition'], 'value')

        secrets_section = payload.get('secrets', {})
        self.assertEqual(secrets_section.get('encryption'), SECRET_ENCRYPTION_SCHEME)
        ciphertext = secrets_section['items'][0]['ciphertext']
        self.assertEqual(decrypt_secret_value(ciphertext, 'passphrase'), 'super-secret')

        self.assertNotIn('change_history', payload)

        download_path = f"/{cid_value}.json"
        self.assertIn(download_path.encode('utf-8'), response.data)

    def test_export_includes_runtime_section(self):
        with self.logged_in():
            response = self.client.post('/export', data={
                'include_source': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            export_record = next(
                (record for record in CID.query.all() if b'"runtime"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        runtime_section = payload.get('runtime')
        self.assertIsInstance(runtime_section, dict)
        python_info = runtime_section.get('python')
        self.assertIsInstance(python_info, dict)
        self.assertEqual(python_info.get('version'), platform.python_version())
        self.assertEqual(python_info.get('implementation'), platform.python_implementation())
        self.assertEqual(python_info.get('executable'), sys.executable or '')
        dependencies = runtime_section.get('dependencies')
        self.assertIsInstance(dependencies, dict)
        flask_info = dependencies.get('flask')
        self.assertIsInstance(flask_info, dict)
        self.assertEqual(flask_info.get('version'), metadata.version('flask'))

        project_files = payload.get('project_files', {})
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)

    def test_export_allows_runtime_only(self):
        with self.logged_in():
            response = self.client.post('/export', data={'submit': True})

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            export_record = next(
                (record for record in CID.query.all() if b'"runtime"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        self.assertIn('runtime', payload)
        self.assertIn('project_files', payload)
        self.assertNotIn('aliases', payload)
        self.assertNotIn('servers', payload)
        self.assertNotIn('variables', payload)
        self.assertNotIn('secrets', payload)
        self.assertNotIn('change_history', payload)
        self.assertNotIn('app_source', payload)
        self.assertNotIn('cid_values', payload)

    def test_export_without_cid_map_excludes_section(self):
        with self.app.app_context():
            server = Server(name='server-one', definition='print("hi")', user_id=self.user_id)
            db.session.add(server)
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/export', data={
                'include_servers': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            cid_records = CID.query.all()
            export_record = next(
                (record for record in cid_records if b'"version"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        project_files = payload.get('project_files', {})
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)
        self.assertNotIn('cid_values', payload)

    def test_export_excludes_unreferenced_cids_by_default(self):
        server_definition = 'print("hi")'
        unreferenced_content = b'unreferenced data'
        unreferenced_cid = format_cid(generate_cid(unreferenced_content))

        with self.app.app_context():
            server = Server(name='server-one', definition=server_definition, user_id=self.user_id)
            unreferenced_record = CID(
                path=f'/{unreferenced_cid}',
                file_data=unreferenced_content,
                file_size=len(unreferenced_content),
                uploaded_by_user_id=self.user_id,
            )
            db.session.add_all([server, unreferenced_record])
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/export', data={
                'include_servers': 'y',
                'include_cid_map': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            export_record = next(
                (record for record in CID.query.all() if b'"cid_values"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        cid_values = payload.get('cid_values', {})
        expected_server_cid = format_cid(generate_cid(server_definition.encode('utf-8')))
        self.assertIn(expected_server_cid, cid_values)
        self.assertNotIn(unreferenced_cid, cid_values)

    def test_export_includes_unreferenced_cids_when_requested(self):
        unreferenced_content = b'unreferenced data'
        unreferenced_cid = format_cid(generate_cid(unreferenced_content))

        with self.app.app_context():
            unreferenced_record = CID(
                path=f'/{unreferenced_cid}',
                file_data=unreferenced_content,
                file_size=len(unreferenced_content),
                uploaded_by_user_id=self.user_id,
            )
            db.session.add(unreferenced_record)
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/export', data={
                'include_aliases': 'y',
                'include_cid_map': 'y',
                'include_unreferenced_cid_data': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            export_record = next(
                (record for record in CID.query.all() if b'"cid_values"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        cid_values = payload.get('cid_values', {})
        self.assertIn(unreferenced_cid, cid_values)
        self.assertEqual(
            cid_values[unreferenced_cid],
            {'encoding': 'utf-8', 'value': unreferenced_content.decode('utf-8')},
        )

    def test_import_reports_missing_selected_content(self):
        definition_text = format_primary_alias_line(
            'literal',
            None,
            '/path',
            alias_name='alias-a',
        )
        payload = json.dumps({'aliases': [{'name': 'alias-a', 'definition': definition_text}]})

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_servers': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assert_flash_present('No server data found in import file.', response.data)

    def test_import_reports_missing_cid_content(self):
        server_definition = 'print("hello")'
        server_cid = format_cid(generate_cid(server_definition.encode('utf-8')))
        payload = json.dumps({
            'servers': [{'name': 'server-c', 'definition_cid': server_cid}],
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_servers': 'y',
                'process_cid_map': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        expected_error = (
            f'Server "server-c" definition with CID "{server_cid}" was not included in the import.'
        )
        self.assert_flash_present(expected_error, response.data)

    def test_export_includes_app_source_cids(self):
        with self.logged_in():
            response = self.client.post('/export', data={
                'include_source': 'y',
                'include_cid_map': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            export_record = next(
                (record for record in CID.query.all() if b'"app_source"' in record.file_data),
                None,
            )

            self.assertIsNotNone(export_record)
            payload = json.loads(export_record.file_data.decode('utf-8'))

        app_source = payload.get('app_source')
        self.assertIsInstance(app_source, dict)
        for section in ('python', 'templates', 'static', 'other'):
            self.assertIn(section, app_source)
            self.assertTrue(app_source[section])

        python_entry = app_source['python'][0]
        self.assertIn('path', python_entry)
        self.assertIn('cid', python_entry)

        base_path = Path(self.app.root_path)
        python_path = base_path / python_entry['path']
        self.assertTrue(python_path.exists())
        expected_cid = format_cid(generate_cid(python_path.read_bytes()))
        self.assertEqual(python_entry['cid'], expected_cid)

        cid_values = payload.get('cid_values', {})
        self.assertIn(python_entry['cid'], cid_values)

    def test_export_excludes_virtualenv_python_files(self):
        base_path = Path(self.app.root_path)
        container_dir = base_path / 'tmp-app-source-check'
        venv_dir = container_dir / 'project' / 'venv'
        dot_venv_dir = container_dir / '.venv'
        virtualenv_files = [
            venv_dir / 'lib' / 'python3.11' / 'ignored.py',
            dot_venv_dir / 'inner.py',
        ]

        try:
            for file_path in virtualenv_files:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text('print("ignored")', encoding='utf-8')

            with self.logged_in():
                response = self.client.post('/export', data={
                    'include_source': 'y',
                    'include_cid_map': 'y',
                    'submit': True,
                })

            self.assertEqual(response.status_code, 200)

            with self.app.app_context():
                export_record = next(
                    (record for record in CID.query.all() if b'"app_source"' in record.file_data),
                    None,
                )

                self.assertIsNotNone(export_record)
                payload = json.loads(export_record.file_data.decode('utf-8'))

            python_entries = payload.get('app_source', {}).get('python', [])
            python_paths = {entry['path'] for entry in python_entries}

            for file_path in virtualenv_files:
                relative_path = file_path.relative_to(base_path).as_posix()
                self.assertNotIn(relative_path, python_paths)
        finally:
            shutil.rmtree(container_dir, ignore_errors=True)

    def test_import_verifies_app_source_matches(self):
        base_path = Path(self.app.root_path)
        python_file = base_path / 'app.py'
        expected_cid = format_cid(generate_cid(python_file.read_bytes()))
        payload = json.dumps({
            'app_source': {
                'python': [
                    {
                        'path': 'app.py',
                        'cid': expected_cid,
                    }
                ]
            }
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_source': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assert_flash_present('All python source files match the export.', response.data)

    def test_import_reports_mismatched_app_source(self):
        mismatched_cid = format_cid(generate_cid(b'invalid'))
        payload = json.dumps({
            'app_source': {
                'python': [
                    {
                        'path': 'app.py',
                        'cid': mismatched_cid,
                    }
                ]
            }
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_source': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assert_flash_present('Source file "app.py" differs from the export.', response.data)

    def test_import_rejects_mismatched_cid_map_entry(self):
        server_definition = 'print("hello")'
        mismatched_cid = format_cid(generate_cid(b'other'))
        payload = json.dumps({
            'servers': [{'name': 'server-c', 'definition_cid': mismatched_cid}],
            'cid_values': {
                mismatched_cid: {'encoding': 'utf-8', 'value': server_definition}
            },
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_servers': 'y',
                'process_cid_map': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        mismatch_error = f'CID "{mismatched_cid}" content did not match its hash and was skipped.'
        self.assert_flash_present(mismatch_error, response.data)
        missing_error = (
            f'Server "server-c" definition with CID "{mismatched_cid}" was not included in the import.'
        )
        self.assert_flash_present(missing_error, response.data)

    def test_import_rejects_invalid_secret_key(self):
        encrypted = encrypt_secret_value('secret', 'correct-key')
        payload = json.dumps({
            'secrets': {
                'encryption': SECRET_ENCRYPTION_SCHEME,
                'items': [
                    {
                        'name': 'secret-one',
                        'ciphertext': encrypted,
                    }
                ],
            }
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_secrets': 'y',
                'secret_key': 'wrong-key',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assert_flash_present('Invalid decryption key for secrets.', response.data)

    def test_successful_import_creates_entries(self):
        encrypted_secret = encrypt_secret_value('value', 'passphrase')
        server_definition = 'print("hello")'
        server_cid = format_cid(generate_cid(server_definition.encode('utf-8')))
        alias_definition = format_primary_alias_line(
            'regex',
            r'^/demo$',
            '/demo',
            ignore_case=True,
            alias_name='alias-b',
        )
        alias_definition = f"{alias_definition}\n# imported alias"
        alias_cid = format_cid(generate_cid(alias_definition.encode('utf-8')))
        payload = json.dumps({
            'aliases': [
                {
                    'name': 'alias-b',
                    'definition_cid': alias_cid,
                }
            ],
            'servers': [{'name': 'server-b', 'definition_cid': server_cid}],
            'variables': [{'name': 'var-b', 'definition': '42'}],
            'secrets': {
                'encryption': SECRET_ENCRYPTION_SCHEME,
                'items': [
                    {'name': 'secret-b', 'ciphertext': encrypted_secret}
                ],
            },
            'cid_values': {
                server_cid: {'encoding': 'utf-8', 'value': server_definition},
                alias_cid: {'encoding': 'utf-8', 'value': alias_definition},
            },
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_aliases': 'y',
                'include_servers': 'y',
                'include_variables': 'y',
                'include_secrets': 'y',
                'process_cid_map': 'y',
                'secret_key': 'passphrase',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Imported 1 alias', response.data)
        self.assertIn(b'1 server', response.data)
        self.assertIn(b'1 variable', response.data)
        self.assertIn(b'1 secret', response.data)

        with self.app.app_context():
            alias = Alias.query.filter_by(user_id=self.user_id, name='alias-b').first()
            self.assertIsNotNone(alias)
            assert alias is not None  # for type checker
            self.assertEqual(alias.target_path, '/demo')
            self.assertEqual(alias.match_type, 'regex')
            self.assertEqual(alias.match_pattern, r'^/demo$')
            self.assertTrue(alias.ignore_case)
            self.assertTrue(
                alias.definition.startswith('^/demo$ -> /demo [regex, ignore-case]')
            )
            self.assertIn('# imported alias', alias.definition)

            server = Server.query.filter_by(user_id=self.user_id, name='server-b').first()
            self.assertIsNotNone(server)
            self.assertEqual(server.definition, 'print("hello")')

            variable = Variable.query.filter_by(user_id=self.user_id, name='var-b').first()
            self.assertIsNotNone(variable)
            self.assertEqual(variable.definition, '42')

            secret = Secret.query.filter_by(user_id=self.user_id, name='secret-b').first()
            self.assertIsNotNone(secret)
            self.assertEqual(secret.definition, 'value')

    def test_import_change_history_creates_events(self):
        timestamp = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        payload = json.dumps({
            'change_history': {
                'aliases': {
                    'alias-b': [
                        {
                            'timestamp': timestamp.isoformat(),
                            'message': 'Created alias',
                            'action': 'save',
                        }
                    ]
                }
            }
        })

        with self.app.app_context():
            definition_text = format_primary_alias_line(
                'literal',
                None,
                '/demo',
                alias_name='alias-b',
            )
            alias = Alias(name='alias-b', user_id=self.user_id, definition=definition_text)
            db.session.add(alias)
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_history': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Imported 1 history event', response.data)

        with self.app.app_context():
            interactions = EntityInteraction.query.filter_by(
                user_id=self.user_id,
                entity_type='alias',
                entity_name='alias-b',
            ).all()
            self.assertEqual(len(interactions), 1)
            self.assertEqual(interactions[0].message, 'Created alias')
            created_at = interactions[0].created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            else:
                created_at = created_at.astimezone(timezone.utc)
            self.assertEqual(created_at, timestamp)


if __name__ == '__main__':
    unittest.main()
