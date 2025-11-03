import base64
import json
import platform
import shutil
import sys
import unittest
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from html import escape
from importlib import metadata
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from types import SimpleNamespace
import tempfile

import routes.import_export as import_export

from alias_definition import format_primary_alias_line
from app import create_app, db
from cid_presenter import format_cid
from cid_utils import generate_cid
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from forms import ExportForm, ImportForm
from models import CID, Alias, EntityInteraction, Secret, Server, Variable


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

    def _load_section(self, payload: dict[str, Any], key: str):
        section_cid = payload.get(key)
        if section_cid is None:
            return None

        self.assertIsInstance(section_cid, str, f'{key} section should reference a CID string')
        cid_values = payload.get('cid_values', {})
        entry = cid_values.get(section_cid)
        content_bytes: bytes | None = None

        if entry is not None:
            # Handle both old format (dict with encoding/value) and new format (string)
            if isinstance(entry, dict):
                encoding = (entry.get('encoding') or 'utf-8').lower()
                value = entry.get('value')
                self.assertIsInstance(value, str, f'{key} CID entry must include string content')
                if encoding == 'base64':
                    content_bytes = base64.b64decode(value.encode('ascii'))
                else:
                    content_bytes = value.encode('utf-8')
            else:
                # New format: entry is directly a UTF-8 string
                self.assertIsInstance(entry, str, f'{key} CID entry must be a string')
                content_bytes = entry.encode('utf-8')
        else:
            with self.app.app_context():
                record = CID.query.filter_by(path=f'/{section_cid}').first()
                self.assertIsNotNone(
                    record,
                    f'CID "{section_cid}" for section "{key}" missing from cid_values and storage',
                )
                assert record is not None  # appease type checker
                file_data = record.file_data
                self.assertIsNotNone(
                    file_data,
                    f'CID "{section_cid}" for section "{key}" did not include stored content',
                )
                content_bytes = bytes(file_data)

        assert content_bytes is not None
        text = content_bytes.decode('utf-8')
        return json.loads(text)

    def _load_export_payload(self) -> tuple[CID, dict[str, Any]]:
        with self.app.app_context():
            export_record: CID | None = None
            export_payload: dict[str, Any] | None = None

            for record in CID.query.all():
                file_data = record.file_data
                if file_data is None:
                    continue
                try:
                    text = bytes(file_data).decode('utf-8')
                except (TypeError, UnicodeDecodeError):
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict) and parsed.get('version') == 6:
                    export_record = record
                    export_payload = parsed
                    break

        self.assertIsNotNone(export_record, 'Expected to find stored export payload')
        assert export_record is not None
        self.assertIsNotNone(export_payload, 'Stored export payload did not decode correctly')
        assert export_payload is not None
        return export_record, export_payload

    def test_export_form_defaults_enable_core_sections(self):
        with self.app.test_request_context():
            form = ExportForm()

        self.assertTrue(form.include_aliases.data)
        self.assertTrue(form.include_servers.data)
        self.assertTrue(form.include_variables.data)

    def test_export_size_endpoint_returns_estimate(self):
        with self.logged_in():
            with ExitStack() as stack:
                mock_builder = stack.enter_context(
                    patch(
                        'routes.import_export._build_export_payload',
                        return_value={'json_payload': '{"size": 1}'},
                    )
                )

                response = self.client.post('/export/size', data={'include_aliases': 'y'})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['size_bytes'], len(b'{"size": 1}'))
        self.assertEqual(payload['formatted_size'], '11 bytes')
        self.assertEqual(mock_builder.call_count, 1)
        _args, kwargs = mock_builder.call_args
        self.assertFalse(kwargs.get('store_content', True))

    def test_export_size_endpoint_returns_errors(self):
        with self.logged_in():
            response = self.client.post('/export/size', data={'include_secrets': 'y'})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        assert payload is not None
        self.assertFalse(payload['ok'])
        self.assertIn('secret_key', payload['errors'])

    def test_export_preview_lists_selected_items(self):
        with self.app.app_context():
            alias = Alias(name='alias-one', definition='echo alias', user_id=self.user_id)
            server = Server(name='server-one', definition='print("hi")', user_id=self.user_id)
            variable = Variable(name='var-one', definition='value', user_id=self.user_id)
            secret = Secret(name='secret-one', definition='secret', user_id=self.user_id)
            db.session.add_all([alias, server, variable, secret])
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertRegex(html, r'name="selected_aliases"[^>]*value="alias-one"[^>]*checked')
        self.assertRegex(html, r'name="selected_servers"[^>]*value="server-one"[^>]*checked')
        self.assertRegex(html, r'name="selected_variables"[^>]*value="var-one"[^>]*checked')
        self.assertIn('<div class="text-muted small fst-italic">Secrets are not selected for export.</div>', html)

    def test_export_preview_respects_disabled_and_template_filters(self):
        with self.app.app_context():
            alias_disabled = Alias(
                name='alias-disabled',
                definition='disabled',
                user_id=self.user_id,
                enabled=False,
            )
            alias_template = Alias(
                name='alias-template',
                definition='template',
                user_id=self.user_id,
                template=True,
            )
            secret = Secret(name='secret-two', definition='top-secret', user_id=self.user_id)
            db.session.add_all([alias_disabled, alias_template, secret])
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')
            html = response.get_data(as_text=True)
            self.assertNotIn('data-export-item-name="alias-disabled"', html)
            self.assertNotIn('data-export-item-name="alias-template"', html)

            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_disabled_aliases': 'y',
                    'include_template_aliases': 'y',
                    'include_secrets': 'y',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertRegex(html, r'name="selected_aliases"[^>]*value="alias-disabled"[^>]*checked')
        self.assertRegex(html, r'name="selected_aliases"[^>]*value="alias-template"[^>]*checked')
        self.assertRegex(html, r'name="selected_secrets"[^>]*value="secret-two"[^>]*checked')
        self.assertNotIn('<div class="text-muted small fst-italic">Secrets are not selected for export.</div>', html)

    def test_export_includes_only_checked_aliases(self):
        with self.app.app_context():
            keep_alias = Alias(name='keep-alias', definition='echo keep', user_id=self.user_id)
            drop_alias = Alias(name='drop-alias', definition='echo drop', user_id=self.user_id)
            db.session.add_all([keep_alias, drop_alias])
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'selected_aliases': ['keep-alias'],
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)
        _record, payload = self._load_export_payload()
        aliases_section = self._load_section(payload, 'aliases')
        self.assertIsInstance(aliases_section, list)
        names = sorted(entry['name'] for entry in aliases_section)
        self.assertEqual(names, ['keep-alias'])

    def test_export_allows_unselecting_all_aliases(self):
        with self.app.app_context():
            alias = Alias(name='only-alias', definition='echo 1', user_id=self.user_id)
            db.session.add(alias)
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'selected_aliases': [import_export._SELECTION_SENTINEL],
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)
        _record, payload = self._load_export_payload()
        self.assertNotIn('aliases', payload)

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

        export_record, payload = self._load_export_payload()
        cid_value = export_record.path.lstrip('/')

        self.assertEqual(payload['version'], 6)

        generated_at_value = self._load_section(payload, 'generated_at')
        self.assertIsInstance(generated_at_value, str)

        project_files = self._load_section(payload, 'project_files')
        self.assertIsInstance(project_files, dict)
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)
        for entry in project_files.values():
            self.assertIn('cid', entry)

        aliases = self._load_section(payload, 'aliases')
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]['name'], 'alias-one')
        self.assertIn('definition_cid', aliases[0])
        self.assertNotIn('definition', aliases[0])
        self.assertIn('enabled', aliases[0])
        self.assertTrue(aliases[0]['enabled'])
        self.assertIn('template', aliases[0])
        self.assertFalse(aliases[0]['template'])
        alias_definition_cid = aliases[0]['definition_cid']

        servers = self._load_section(payload, 'servers')
        self.assertEqual(len(servers), 1)
        self.assertIn('definition_cid', servers[0])
        self.assertNotIn('definition', servers[0])
        self.assertIn('enabled', servers[0])
        self.assertTrue(servers[0]['enabled'])
        self.assertIn('template', servers[0])
        self.assertFalse(servers[0]['template'])

        cid_values = payload.get('cid_values', {})
        self.assertIn(alias_definition_cid, cid_values)
        self.assertEqual(
            cid_values[alias_definition_cid],
            definition_text,
        )
        self.assertIn(servers[0]['definition_cid'], cid_values)
        self.assertEqual(
            cid_values[servers[0]['definition_cid']],
            'print("hi")',
        )
        for entry in project_files.values():
            self.assertIn(entry['cid'], cid_values)

        variables = self._load_section(payload, 'variables')
        self.assertEqual(variables[0]['definition'], 'value')
        self.assertIn('enabled', variables[0])
        self.assertTrue(variables[0]['enabled'])
        self.assertIn('template', variables[0])
        self.assertFalse(variables[0]['template'])

        secrets_section = self._load_section(payload, 'secrets')
        self.assertEqual(secrets_section.get('encryption'), SECRET_ENCRYPTION_SCHEME)
        self.assertIn('enabled', secrets_section['items'][0])
        self.assertTrue(secrets_section['items'][0]['enabled'])
        self.assertIn('template', secrets_section['items'][0])
        self.assertFalse(secrets_section['items'][0]['template'])
        ciphertext = secrets_section['items'][0]['ciphertext']
        self.assertEqual(decrypt_secret_value(ciphertext, 'passphrase'), 'super-secret')

        self.assertNotIn('change_history', payload)

        download_path = f"/{cid_value}.json"
        self.assertIn(download_path.encode('utf-8'), response.data)

    def test_export_and_import_preserve_enablement(self):
        alias_definition = format_primary_alias_line(
            'literal',
            '/alias-disabled',
            '/target',
            alias_name='alias-disabled',
        )

        with self.app.app_context():
            db.session.add_all(
                [
                    Alias(
                        name='alias-disabled',
                        user_id=self.user_id,
                        definition=alias_definition,
                        enabled=False,
                    ),
                    Server(
                        name='server-disabled',
                        user_id=self.user_id,
                        definition='def main():\n    return "disabled"\n',
                        enabled=False,
                    ),
                    Variable(
                        name='variable-disabled',
                        user_id=self.user_id,
                        definition='value',
                        enabled=False,
                    ),
                    Secret(
                        name='secret-disabled',
                        user_id=self.user_id,
                        definition='super-secret',
                        enabled=False,
                    ),
                ]
            )
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_disabled_aliases': 'y',
                    'include_servers': 'y',
                    'include_disabled_servers': 'y',
                    'include_variables': 'y',
                    'include_disabled_variables': 'y',
                    'include_secrets': 'y',
                    'include_disabled_secrets': 'y',
                    'include_history': '',
                    'include_cid_map': 'y',
                    'secret_key': 'passphrase',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        alias_entries = self._load_section(payload, 'aliases')
        server_entries = self._load_section(payload, 'servers')
        variable_entries = self._load_section(payload, 'variables')
        secrets_section = self._load_section(payload, 'secrets')

        self.assertFalse(alias_entries[0]['enabled'])
        self.assertIn('template', alias_entries[0])
        self.assertFalse(alias_entries[0]['template'])
        self.assertFalse(server_entries[0]['enabled'])
        self.assertIn('template', server_entries[0])
        self.assertFalse(server_entries[0]['template'])
        self.assertFalse(variable_entries[0]['enabled'])
        self.assertIn('template', variable_entries[0])
        self.assertFalse(variable_entries[0]['template'])
        self.assertFalse(secrets_section['items'][0]['enabled'])
        self.assertIn('template', secrets_section['items'][0])
        self.assertFalse(secrets_section['items'][0]['template'])

        with self.app.app_context():
            Alias.query.delete()
            Server.query.delete()
            Variable.query.delete()
            Secret.query.delete()
            db.session.commit()

            cid_map, errors = import_export._parse_cid_values_section(payload.get('cid_values'))
            self.assertEqual(errors, [])

            alias_count, alias_errors = import_export._import_aliases(
                self.user_id, alias_entries, cid_map
            )
            server_count, server_errors = import_export._import_servers(
                self.user_id, server_entries, cid_map
            )
            variable_count, variable_errors = import_export._import_variables(
                self.user_id, variable_entries
            )
            secret_count, secret_errors = import_export._import_secrets(
                self.user_id, secrets_section, 'passphrase'
            )

            self.assertEqual(alias_errors, [])
            self.assertEqual(server_errors, [])
            self.assertEqual(variable_errors, [])
            self.assertEqual(secret_errors, [])
            self.assertEqual(alias_count, 1)
            self.assertEqual(server_count, 1)
            self.assertEqual(variable_count, 1)
            self.assertEqual(secret_count, 1)

            imported_alias = Alias.query.filter_by(name='alias-disabled').first()
            imported_server = Server.query.filter_by(name='server-disabled').first()
            imported_variable = Variable.query.filter_by(name='variable-disabled').first()
            imported_secret = Secret.query.filter_by(name='secret-disabled').first()

            self.assertIsNotNone(imported_alias)
            self.assertIsNotNone(imported_server)
            self.assertIsNotNone(imported_variable)
            self.assertIsNotNone(imported_secret)

            assert imported_alias and imported_server and imported_variable and imported_secret
            self.assertFalse(imported_alias.enabled)
            self.assertFalse(imported_server.enabled)
            self.assertFalse(imported_variable.enabled)
            self.assertFalse(imported_secret.enabled)

    def test_export_omits_disabled_items_without_selection(self):
        alias_definition = format_primary_alias_line(
            'literal',
            '/disabled',
            '/target',
            alias_name='disabled-alias',
        )

        with self.app.app_context():
            db.session.add_all(
                [
                    Alias(
                        name='disabled-alias',
                        user_id=self.user_id,
                        definition=alias_definition,
                        enabled=False,
                    ),
                    Server(
                        name='disabled-server',
                        user_id=self.user_id,
                        definition='print("disabled")',
                        enabled=False,
                    ),
                    Variable(
                        name='disabled-variable',
                        user_id=self.user_id,
                        definition='value',
                        enabled=False,
                    ),
                    Secret(
                        name='disabled-secret',
                        user_id=self.user_id,
                        definition='secret-value',
                        enabled=False,
                    ),
                ]
            )
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_servers': 'y',
                    'include_variables': 'y',
                    'include_secrets': 'y',
                    'secret_key': 'key',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        self.assertIsNone(self._load_section(payload, 'aliases'))
        self.assertIsNone(self._load_section(payload, 'servers'))

        variable_entries = self._load_section(payload, 'variables')
        self.assertEqual(variable_entries, [])

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertEqual(secrets_section.get('items'), [])

    def test_export_requires_template_selection_for_templates(self):
        alias_definition = format_primary_alias_line(
            'literal',
            '/template',
            '/target',
            alias_name='template-alias',
        )

        with self.app.app_context():
            db.session.add_all(
                [
                    Alias(
                        name='template-alias',
                        user_id=self.user_id,
                        definition=alias_definition,
                        template=True,
                    ),
                    Server(
                        name='template-server',
                        user_id=self.user_id,
                        definition='print("template")',
                        template=True,
                    ),
                    Variable(
                        name='template-variable',
                        user_id=self.user_id,
                        definition='value',
                        template=True,
                    ),
                    Secret(
                        name='template-secret',
                        user_id=self.user_id,
                        definition='secret-value',
                        template=True,
                    ),
                ]
            )
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_servers': 'y',
                    'include_variables': 'y',
                    'include_secrets': 'y',
                    'secret_key': 'key',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        self.assertIsNone(self._load_section(payload, 'aliases'))
        self.assertIsNone(self._load_section(payload, 'servers'))

        variable_entries = self._load_section(payload, 'variables')
        self.assertEqual(variable_entries, [])

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertEqual(secrets_section.get('items'), [])

        with self.app.app_context():
            CID.query.delete()
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_template_aliases': 'y',
                    'include_servers': 'y',
                    'include_template_servers': 'y',
                    'include_variables': 'y',
                    'include_template_variables': 'y',
                    'include_secrets': 'y',
                    'include_template_secrets': 'y',
                    'secret_key': 'key',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        alias_entries = self._load_section(payload, 'aliases')
        assert alias_entries is not None
        self.assertEqual(len(alias_entries), 1)
        self.assertTrue(alias_entries[0]['template'])

        server_entries = self._load_section(payload, 'servers')
        assert server_entries is not None
        self.assertEqual(len(server_entries), 1)
        self.assertTrue(server_entries[0]['template'])

        variable_entries = self._load_section(payload, 'variables')
        self.assertEqual(len(variable_entries), 1)
        self.assertTrue(variable_entries[0]['template'])

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertEqual(len(secrets_section.get('items', [])), 1)
        self.assertTrue(secrets_section['items'][0]['template'])

    def test_export_includes_disabled_templates_with_template_selection(self):
        alias_definition = format_primary_alias_line(
            'literal',
            '/disabled-template',
            '/target',
            alias_name='disabled-template-alias',
        )

        with self.app.app_context():
            db.session.add_all(
                [
                    Alias(
                        name='disabled-template-alias',
                        user_id=self.user_id,
                        definition=alias_definition,
                        enabled=False,
                        template=True,
                    ),
                    Server(
                        name='disabled-template-server',
                        user_id=self.user_id,
                        definition='print("disabled template")',
                        enabled=False,
                        template=True,
                    ),
                    Variable(
                        name='disabled-template-variable',
                        user_id=self.user_id,
                        definition='value',
                        enabled=False,
                        template=True,
                    ),
                    Secret(
                        name='disabled-template-secret',
                        user_id=self.user_id,
                        definition='secret-value',
                        enabled=False,
                        template=True,
                    ),
                ]
            )
            db.session.commit()

        with self.logged_in():
            response = self.client.post(
                '/export',
                data={
                    'include_aliases': 'y',
                    'include_template_aliases': 'y',
                    'include_servers': 'y',
                    'include_template_servers': 'y',
                    'include_variables': 'y',
                    'include_template_variables': 'y',
                    'include_secrets': 'y',
                    'include_template_secrets': 'y',
                    'secret_key': 'key',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        alias_entries = self._load_section(payload, 'aliases')
        assert alias_entries is not None
        self.assertEqual(alias_entries[0]['enabled'], False)
        self.assertTrue(alias_entries[0]['template'])

        server_entries = self._load_section(payload, 'servers')
        assert server_entries is not None
        self.assertEqual(server_entries[0]['enabled'], False)
        self.assertTrue(server_entries[0]['template'])

        variable_entries = self._load_section(payload, 'variables')
        self.assertEqual(variable_entries[0]['enabled'], False)
        self.assertTrue(variable_entries[0]['template'])

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertEqual(secrets_section['items'][0]['enabled'], False)
        self.assertTrue(secrets_section['items'][0]['template'])

    def test_export_includes_runtime_section(self):
        with self.logged_in():
            response = self.client.post('/export', data={
                'include_source': 'y',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        runtime_section = self._load_section(payload, 'runtime')
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

        project_files = self._load_section(payload, 'project_files')
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)

    def test_export_allows_runtime_only(self):
        with self.logged_in():
            response = self.client.post('/export', data={'submit': True})

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        self.assertIn('runtime', payload)
        runtime_section = self._load_section(payload, 'runtime')
        self.assertIsInstance(runtime_section, dict)

        project_files = self._load_section(payload, 'project_files')
        self.assertIsInstance(project_files, dict)
        self.assertNotIn('aliases', payload)
        self.assertNotIn('servers', payload)
        self.assertNotIn('variables', payload)
        self.assertNotIn('secrets', payload)
        self.assertNotIn('change_history', payload)
        self.assertNotIn('app_source', payload)
        self.assertNotIn('cid_values', payload)

    def test_export_without_cid_map_omits_content_map(self):
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

        _, payload = self._load_export_payload()

        project_files = self._load_section(payload, 'project_files')
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)
        servers = self._load_section(payload, 'servers')
        server_definition_cid = servers[0]['definition_cid']

        self.assertNotIn('cid_values', payload)

        with self.app.app_context():
            runtime_record = CID.query.filter_by(path=f"/{payload['runtime']}").first()
            self.assertIsNotNone(runtime_record)
            assert runtime_record is not None
            self.assertIsNotNone(runtime_record.file_data)

            server_record = CID.query.filter_by(path=f'/{server_definition_cid}').first()
            self.assertIsNotNone(server_record)
            assert server_record is not None
            self.assertIsNotNone(server_record.file_data)

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

        _, payload = self._load_export_payload()

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

        _, payload = self._load_export_payload()

        cid_values = payload.get('cid_values', {})
        self.assertIn(unreferenced_cid, cid_values)
        self.assertEqual(
            cid_values[unreferenced_cid],
            unreferenced_content.decode('utf-8'),
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

        _, payload = self._load_export_payload()

        app_source = self._load_section(payload, 'app_source')
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

            _, payload = self._load_export_payload()

            app_source_section = self._load_section(payload, 'app_source')
            python_entries = (app_source_section or {}).get('python', [])
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

    def test_source_entry_helpers_validate_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / 'module').mkdir()
            local_file = base_path / 'module' / 'example.py'
            file_bytes = b'print("hello")\n'
            local_file.write_bytes(file_bytes)

            warnings: list[str] = []
            parsed = import_export._parse_source_entry(
                {'path': 'module/example.py', 'cid': 'demo-cid'},
                'Python Source Files',
                warnings,
            )
            self.assertIsNotNone(parsed)
            assert parsed is not None
            self.assertEqual(parsed.relative_path.as_posix(), 'module/example.py')

            resolved = import_export._resolve_source_entry(
                parsed,
                base_path,
                base_path.resolve(),
                warnings,
            )
            self.assertEqual(resolved, local_file)

            content = import_export._load_source_entry_bytes(resolved, parsed, warnings)
            self.assertEqual(content, file_bytes)

            correct_cid = format_cid(generate_cid(file_bytes))
            parsed.expected_cid = correct_cid
            self.assertTrue(import_export._source_entry_matches_export(parsed, content, warnings))
            self.assertEqual(warnings, [])

            parsed.expected_cid = 'different'
            self.assertFalse(import_export._source_entry_matches_export(parsed, content, warnings))
            self.assertIn('differs from the export', warnings[-1])

    def test_prepare_alias_import_uses_definition_cid(self):
        alias_line = format_primary_alias_line(
            'glob',
            '/demo/*',
            '/target',
            ignore_case=True,
            alias_name='example',
        )
        definition_text = f"{alias_line}\n# sample"
        cid_map = {'alias-cid': definition_text.encode('utf-8')}
        errors: list[str] = []

        prepared = import_export._prepare_alias_import(
            {'name': 'example', 'definition_cid': 'alias-cid'},
            set(),
            cid_map,
            errors,
        )

        self.assertIsNotNone(prepared)
        assert prepared is not None
        self.assertEqual(prepared.name, 'example')
        self.assertIn(alias_line, prepared.definition)
        self.assertTrue(prepared.enabled)
        self.assertEqual(errors, [])

    def test_store_cid_entry_optional_behaviour(self):
        cid_entries: dict[str, dict[str, str]] = {}
        import_export._store_cid_entry('test-cid', b'data', cid_entries, include_optional=False)
        self.assertEqual(cid_entries, {})

        import_export._store_cid_entry('test-cid', b'data', cid_entries, include_optional=True)
        self.assertIn('test-cid', cid_entries)
        original_entry = cid_entries['test-cid']

        import_export._store_cid_entry('test-cid', b'updated', cid_entries, include_optional=True)
        self.assertIs(cid_entries['test-cid'], original_entry)

    def test_import_section_records_summary(self):
        data = {'aliases': ['entry']}
        context = import_export._ImportContext(
            form=cast(ImportForm, object()),
            user_id='user',
            change_message='',
            raw_payload='{}',
            data=data,
        )

        plan = import_export._SectionImportPlan(
            include=True,
            section_key='aliases',
            importer=lambda section: (2, [])
            if section == ['entry']
            else (0, ['wrong section']),
            singular_label='alias',
            plural_label='aliases',
        )

        count = import_export._import_section(context, plan)

        self.assertEqual(count, 2)
        self.assertEqual(context.errors, [])
        self.assertEqual(context.summaries, ['2 aliases'])

        sentinel: dict[str, Any] = {}
        skipped_plan = import_export._SectionImportPlan(
            include=False,
            section_key='aliases',
            importer=lambda section: sentinel.setdefault('called', True) or (0, []),
            singular_label='alias',
            plural_label='aliases',
        )
        import_export._import_section(context, skipped_plan)
        self.assertNotIn('called', sentinel)

    def test_import_section_rejects_invalid_plan_shape(self):
        context = import_export._ImportContext(
            form=cast(ImportForm, object()),
            user_id='user',
            change_message='',
            raw_payload='{}',
            data={},
        )

        with self.assertRaises(AttributeError):
            import_export._import_section(
                context,
                cast(import_export._SectionImportPlan, object()),
            )

    def test_build_export_payload_collects_aliases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / 'pyproject.toml').write_text('[project]\nname = "demo"\n', 'utf-8')
            (base_path / 'requirements.txt').write_text('flask\n', 'utf-8')

            alias_line = format_primary_alias_line(
                'glob',
                '/demo/*',
                '/target',
                ignore_case=True,
                alias_name='example',
            )
            alias_definition = f"{alias_line}\n# export"

            class StoreBytesStub:
                def __init__(self):
                    self.calls: list[bytes] = []

                def __call__(self, content: bytes, user_id: str) -> str:
                    self.calls.append(content)
                    return f'cid-{len(self.calls)}'

            store_bytes_stub = StoreBytesStub()

            with self.app.app_context():
                with ExitStack() as stack:
                    stack.enter_context(patch('routes.import_export._app_root_path', return_value=base_path))
                    stack.enter_context(patch('routes.import_export.get_user_aliases', return_value=[SimpleNamespace(name='example', definition=alias_definition)]))
                    stack.enter_context(patch('routes.import_export.get_user_servers', return_value=[]))
                    stack.enter_context(patch('routes.import_export.get_user_variables', return_value=[]))
                    stack.enter_context(patch('routes.import_export.get_user_secrets', return_value=[]))
                    stack.enter_context(patch('routes.import_export.get_user_uploads', return_value=[]))
                    stack.enter_context(patch('routes.import_export._gather_change_history', return_value={}))
                    stack.enter_context(patch('routes.import_export.store_cid_from_bytes', side_effect=store_bytes_stub))
                    stack.enter_context(patch('routes.import_export.cid_path', return_value='/downloads/export.json'))

                    with self.app.test_request_context():
                        form = ExportForm()
                        form.include_aliases.data = True
                        form.include_disabled_aliases.data = False
                        form.include_template_aliases.data = False
                        form.include_cid_map.data = True
                        form.include_unreferenced_cid_data.data = False
                        form.include_servers.data = False
                        form.include_disabled_servers.data = False
                        form.include_template_servers.data = False
                        form.include_variables.data = False
                        form.include_disabled_variables.data = False
                        form.include_template_variables.data = False
                        form.include_secrets.data = False
                        form.include_disabled_secrets.data = False
                        form.include_template_secrets.data = False
                        form.include_history.data = False
                        form.include_source.data = False

                        result = import_export._build_export_payload(form, self.user_id)

        self.assertEqual(result['cid_value'], f'cid-{len(store_bytes_stub.calls)}')
        self.assertEqual(result['download_path'], '/downloads/export.json')
        self.assertGreaterEqual(len(store_bytes_stub.calls), 1)
        ordered_pairs = json.loads(result['json_payload'], object_pairs_hook=list)
        top_level_keys = [key for key, _ in ordered_pairs]
        self.assertIn('cid_values', top_level_keys)
        self.assertEqual(top_level_keys[:-1], sorted(top_level_keys[:-1]))
        self.assertEqual(top_level_keys[-1], 'cid_values')
        payload = json.loads(store_bytes_stub.calls[-1].decode('utf-8'))
        self.assertIn('aliases', payload)
        self.assertIn('cid_values', payload)
        cid_values = payload['cid_values']
        self.assertTrue(
            any('export' in entry.get('value', '') for entry in cid_values.values())
        )

    def test_process_import_submission_returns_form_on_empty_payload(self):
        with self.app.test_request_context():
            form = ImportForm()

            with ExitStack() as stack:
                stack.enter_context(patch('routes.import_export._load_import_payload', return_value=' '))
                stack.enter_context(patch('routes.import_export.flash'))

                render_calls: list[str] = []

                def render_form() -> str:
                    render_calls.append('called')
                    return 'rendered-form'

                response = import_export._process_import_submission(form, 'note', render_form)

        self.assertEqual(response, 'rendered-form')
        self.assertEqual(render_calls, ['called'])

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

    def test_export_cid_values_as_utf8_strings(self):
        """Test that exported CID values are UTF-8 strings without encoding field."""

        definition_text = 'print("Hello, 世界")'  # UTF-8 content with non-ASCII chars

        with self.logged_in():
            # Create a server with UTF-8 content
            response = self.client.post('/servers', data={
                'name': 'test-server',
                'definition': definition_text,
                'enabled': 'y',
                'template': '',
                'submit': True,
            })
            self.assertEqual(response.status_code, 302)

            # Export the server
            response = self.client.post('/export', data={
                'include_servers': 'y',
                'include_cid_map': 'y',
                'submit': True,
            })
            self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()
        cid_values = payload.get('cid_values', {})

        # Verify CID values are stored as plain strings, not dicts
        for cid, value in cid_values.items():
            self.assertIsInstance(value, str, f'CID value for {cid} should be a string')
            self.assertNotIsInstance(value, dict, f'CID value for {cid} should not be a dict')

        # Verify the specific server definition is present as a string
        servers = payload.get('servers', [])
        self.assertEqual(len(servers), 1)
        definition_cid = servers[0]['definition_cid']
        self.assertIn(definition_cid, cid_values)
        self.assertEqual(cid_values[definition_cid], definition_text)

    def test_import_cid_values_from_utf8_strings(self):
        """Test that import can handle CID values as plain UTF-8 strings."""

        server_definition = 'print("Hello from new format")'
        server_cid = format_cid(generate_cid(server_definition.encode('utf-8')))

        # Create import payload with new format (string values, no encoding field)
        payload = json.dumps({
            'servers': [{'name': 'imported-server', 'definition_cid': server_cid}],
            'cid_values': {
                server_cid: server_definition,  # Plain string, no encoding dict
            },
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'submit': True,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 server', response.data)

            # Verify the server was imported correctly
            with self.app.app_context():
                server = Server.query.filter_by(user_id=self.user_id, name='imported-server').first()
                self.assertIsNotNone(server)
                self.assertEqual(server.definition, server_definition)

    def test_import_cid_values_backward_compatibility(self):
        """Test that import still handles old format with encoding field."""

        server_definition = 'print("Hello from old format")'
        server_cid = format_cid(generate_cid(server_definition.encode('utf-8')))

        # Create import payload with old format (dict with encoding and value fields)
        payload = json.dumps({
            'servers': [{'name': 'old-format-server', 'definition_cid': server_cid}],
            'cid_values': {
                server_cid: {'encoding': 'utf-8', 'value': server_definition},
            },
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'submit': True,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 server', response.data)

            # Verify the server was imported correctly
            with self.app.app_context():
                server = Server.query.filter_by(user_id=self.user_id, name='old-format-server').first()
                self.assertIsNotNone(server)
                self.assertEqual(server.definition, server_definition)

    def test_import_defaults_to_utf8_without_encoding(self):
        """Test that import defaults to UTF-8 when no encoding is specified."""

        # Test with non-ASCII UTF-8 content
        content_with_unicode = 'Hello 世界 🌍'
        alias_definition = format_primary_alias_line('test', content_with_unicode)
        alias_cid = format_cid(generate_cid(alias_definition.encode('utf-8')))

        # Import with plain string (should default to UTF-8)
        payload = json.dumps({
            'aliases': [{'name': 'test-alias', 'definition_cid': alias_cid}],
            'cid_values': {
                alias_cid: alias_definition,
            },
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'submit': True,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 alias', response.data)

            # Verify the alias was imported with correct UTF-8 content
            with self.app.app_context():
                alias = Alias.query.filter_by(user_id=self.user_id, name='test-alias').first()
                self.assertIsNotNone(alias)
                self.assertEqual(alias.definition, alias_definition)


if __name__ == '__main__':
    unittest.main()
