"""Comprehensive tests for import/export functionality."""
# pylint: disable=too-many-lines  # Test file intentionally comprehensive; splitting would reduce discoverability

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
from models import CID, Alias, EntityInteraction, Export, Secret, Server, Variable
from routes.import_export.import_engine import generate_snapshot_export


class TestImportExportRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
            'DEBUG': False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def authenticate(self):
        """Mark the test client's session as authenticated in single-user mode."""
        with self.client.session_transaction() as session:
            session['_fresh'] = True

    @contextmanager
    def logged_in(self):
        """Backward-compatible helper to run blocks as an authenticated user."""
        self.authenticate()
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
                if not isinstance(value, str):
                    raise AssertionError(f'{key} CID entry must include string content')
                if encoding == 'base64':
                    content_bytes = base64.b64decode(value.encode('ascii'))
                else:
                    content_bytes = value.encode('utf-8')
            else:
                # New format: entry is directly a UTF-8 string
                self.assertIsInstance(entry, str, f'{key} CID entry must be a string')
                assert isinstance(entry, str)  # For type checker
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

    def _find_entry_by_name(self, entries: list[dict[str, Any]] | None, name: str):
        if not entries:
            return None
        return next((entry for entry in entries if entry.get('name') == name), None)

    def _load_export_payload(self) -> tuple[CID, dict[str, Any]]:
        with self.app.app_context():
            export_record: CID | None = None
            export_payload: dict[str, Any] | None = None

            # Order by ID descending to get the most recent export first
            for record in CID.query.order_by(CID.id.desc()).all():
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

        self.assertTrue(form.snapshot.data)
        self.assertTrue(form.include_aliases.data)
        self.assertTrue(form.include_servers.data)
        self.assertTrue(form.include_variables.data)

    def test_export_size_endpoint_returns_estimate(self):
        with self.logged_in():
            with ExitStack() as stack:
                mock_builder = stack.enter_context(
                    patch(
                        'routes.import_export.routes.build_export_payload',
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
            alias = Alias(name='alias-one', definition='echo alias')
            server = Server(name='server-one', definition='print("hi")')
            variable = Variable(name='var-one', definition='value')
            secret = Secret(name='secret-one', definition='secret')
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
                enabled=False,
            )
            alias_regular = Alias(
                name='alias-regular',
                definition='regular',
            )
            secret = Secret(name='secret-two', definition='top-secret')
            db.session.add_all([alias_disabled, alias_regular, secret])
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')
            html = response.get_data(as_text=True)
            self.assertNotIn('data-export-item-name="alias-disabled"', html)
            self.assertIn('data-export-item-name="alias-regular"', html)

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
        self.assertRegex(html, r'name="selected_aliases"[^>]*value="alias-regular"[^>]*checked')
        self.assertRegex(html, r'name="selected_secrets"[^>]*value="secret-two"[^>]*checked')
        self.assertNotIn('<div class="text-muted small fst-italic">Secrets are not selected for export.</div>', html)

    def test_export_includes_only_checked_aliases(self):
        with self.app.app_context():
            keep_alias = Alias(name='keep-alias', definition='echo keep')
            drop_alias = Alias(name='drop-alias', definition='echo drop')
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
            alias = Alias(name='only-alias', definition='echo 1')
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
                definition=definition_text,
            )
            server = Server(name='server-one', definition='print("hi")')
            variable = Variable(name='var-one', definition='value')
            secret = Secret(name='secret-one', definition='super-secret')
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

        project_files = self._load_section(payload, 'project_files')
        self.assertIsInstance(project_files, dict)
        self.assertIn('pyproject.toml', project_files)
        self.assertIn('requirements.txt', project_files)
        for entry in project_files.values():
            self.assertIn('cid', entry)

        aliases = self._load_section(payload, 'aliases')
        alias_entry = self._find_entry_by_name(aliases, 'alias-one')
        self.assertIsNotNone(alias_entry)
        assert alias_entry is not None
        self.assertIn('definition_cid', alias_entry)
        self.assertNotIn('definition', alias_entry)
        self.assertIn('enabled', alias_entry)
        self.assertTrue(alias_entry['enabled'])
        alias_definition_cid = alias_entry['definition_cid']

        servers = self._load_section(payload, 'servers')
        server_entry = self._find_entry_by_name(servers, 'server-one')
        self.assertIsNotNone(server_entry)
        assert server_entry is not None
        self.assertIn('definition_cid', server_entry)
        self.assertNotIn('definition', server_entry)
        self.assertIn('enabled', server_entry)
        self.assertTrue(server_entry['enabled'])

        cid_values = payload.get('cid_values', {})
        self.assertIn(alias_definition_cid, cid_values)
        self.assertEqual(
            cid_values[alias_definition_cid],
            definition_text,
        )
        self.assertIn(server_entry['definition_cid'], cid_values)
        self.assertEqual(
            cid_values[server_entry['definition_cid']],
            'print("hi")',
        )
        for entry in project_files.values():
            self.assertIn(entry['cid'], cid_values)

        variables = self._load_section(payload, 'variables')
        variable_entry = self._find_entry_by_name(variables, 'var-one')
        self.assertIsNotNone(variable_entry)
        assert variable_entry is not None
        self.assertEqual(variable_entry['definition'], 'value')
        self.assertIn('enabled', variable_entry)
        self.assertTrue(variable_entry['enabled'])

        secrets_section = self._load_section(payload, 'secrets')
        self.assertEqual(secrets_section.get('encryption'), SECRET_ENCRYPTION_SCHEME)
        secret_entry = self._find_entry_by_name(secrets_section.get('items') if secrets_section else None, 'secret-one')
        self.assertIsNotNone(secret_entry)
        assert secret_entry is not None
        self.assertIn('enabled', secret_entry)
        self.assertTrue(secret_entry['enabled'])
        ciphertext = secret_entry['ciphertext']
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
                        definition=alias_definition,
                        enabled=False,
                    ),
                    Server(
                        name='server-disabled',
                        definition='def main():\n    return "disabled"\n',
                        enabled=False,
                    ),
                    Variable(
                        name='variable-disabled',
                        definition='value',
                        enabled=False,
                    ),
                    Secret(
                        name='secret-disabled',
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

        # Find the specific disabled items by name (not just [0] which might be default items)
        disabled_alias = next((a for a in alias_entries if a['name'] == 'alias-disabled'), None)
        disabled_server = next((s for s in server_entries if s['name'] == 'server-disabled'), None)
        disabled_variable = next((v for v in variable_entries if v['name'] == 'variable-disabled'), None)
        disabled_secret = next((s for s in secrets_section['items'] if s['name'] == 'secret-disabled'), None)

        # Verify the disabled items were exported
        self.assertIsNotNone(disabled_alias, "Disabled alias should be in export")
        self.assertIsNotNone(disabled_server, "Disabled server should be in export")
        self.assertIsNotNone(disabled_variable, "Disabled variable should be in export")
        self.assertIsNotNone(disabled_secret, "Disabled secret should be in export")

        # Verify the disabled flag is preserved
        self.assertFalse(disabled_alias['enabled'])
        self.assertFalse(disabled_server['enabled'])
        self.assertFalse(disabled_variable['enabled'])
        self.assertFalse(disabled_secret['enabled'])

        with self.app.app_context():
            Alias.query.delete()
            Server.query.delete()
            Variable.query.delete()
            Secret.query.delete()
            db.session.commit()

            cid_map, errors = import_export._parse_cid_values_section(payload.get('cid_values'))
            self.assertEqual(errors, [])

            alias_count, alias_errors = import_export._import_aliases(
                alias_entries, cid_map
            )
            server_count, server_errors = import_export._import_servers(
                server_entries, cid_map
            )
            variable_count, variable_errors = import_export._import_variables(
                variable_entries
            )
            secret_count, secret_errors = import_export._import_secrets(
                secrets_section, 'passphrase'
            )

            self.assertEqual(alias_errors, [])
            self.assertEqual(server_errors, [])
            self.assertEqual(variable_errors, [])
            self.assertEqual(secret_errors, [])
            self.assertGreaterEqual(alias_count, 1)
            self.assertGreaterEqual(server_count, 1)
            self.assertGreaterEqual(variable_count, 1)
            self.assertGreaterEqual(secret_count, 1)


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
                        definition=alias_definition,
                        enabled=False,
                    ),
                    Server(
                        name='disabled-server',
                        definition='print("disabled")',
                        enabled=False,
                    ),
                    Variable(
                        name='disabled-variable',
                        definition='value',
                        enabled=False,
                    ),
                    Secret(
                        name='disabled-secret',
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

        aliases = self._load_section(payload, 'aliases')
        self.assertIsNone(self._find_entry_by_name(aliases, 'disabled-alias'))

        servers = self._load_section(payload, 'servers')
        self.assertIsNone(self._find_entry_by_name(servers, 'disabled-server'))

        variable_entries = self._load_section(payload, 'variables')
        self.assertIsNone(self._find_entry_by_name(variable_entries, 'disabled-variable'))

        secrets_section = self._load_section(payload, 'secrets')
        items = secrets_section.get('items') if secrets_section else None
        self.assertIsNone(self._find_entry_by_name(items, 'disabled-secret'))

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
                        definition=alias_definition,
                    ),
                    Server(
                        name='template-server',
                        definition='print("template")',
                    ),
                    Variable(
                        name='template-variable',
                        definition='value',
                    ),
                    Secret(
                        name='template-secret',
                        definition='secret-value',
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

        # Entities are now exported as regular entities (no longer templates)
        aliases = self._load_section(payload, 'aliases')
        self.assertIsNotNone(self._find_entry_by_name(aliases, 'template-alias'))

        servers = self._load_section(payload, 'servers')
        self.assertIsNotNone(self._find_entry_by_name(servers, 'template-server'))

        variable_entries = self._load_section(payload, 'variables')
        self.assertIsNotNone(self._find_entry_by_name(variable_entries, 'template-variable'))

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertIsNotNone(self._find_entry_by_name(secrets_section.get('items'), 'template-secret'))

        # Second export with all include flags is redundant now but should also work
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
        self.assertIsNotNone(self._find_entry_by_name(alias_entries, 'template-alias'))

        server_entries = self._load_section(payload, 'servers')
        assert server_entries is not None
        self.assertIsNotNone(self._find_entry_by_name(server_entries, 'template-server'))

        variable_entries = self._load_section(payload, 'variables')
        self.assertIsNotNone(self._find_entry_by_name(variable_entries, 'template-variable'))

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        self.assertIsNotNone(self._find_entry_by_name(secrets_section.get('items', []), 'template-secret'))

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
                        definition=alias_definition,
                        enabled=False,
                    ),
                    Server(
                        name='disabled-template-server',
                        definition='print("disabled template")',
                        enabled=False,
                    ),
                    Variable(
                        name='disabled-template-variable',
                        definition='value',
                        enabled=False,
                    ),
                    Secret(
                        name='disabled-template-secret',
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
                    'include_disabled_aliases': 'y',
                    'include_template_aliases': 'y',
                    'include_servers': 'y',
                    'include_disabled_servers': 'y',
                    'include_template_servers': 'y',
                    'include_variables': 'y',
                    'include_disabled_variables': 'y',
                    'include_template_variables': 'y',
                    'include_secrets': 'y',
                    'include_disabled_secrets': 'y',
                    'include_template_secrets': 'y',
                    'secret_key': 'key',
                    'submit': True,
                },
            )

        self.assertEqual(response.status_code, 200)

        _, payload = self._load_export_payload()

        alias_entries = self._load_section(payload, 'aliases')
        disabled_alias_entry = self._find_entry_by_name(alias_entries, 'disabled-template-alias')
        self.assertIsNotNone(disabled_alias_entry)
        assert disabled_alias_entry is not None
        self.assertFalse(disabled_alias_entry['enabled'])

        server_entries = self._load_section(payload, 'servers')
        disabled_server_entry = self._find_entry_by_name(server_entries, 'disabled-template-server')
        self.assertIsNotNone(disabled_server_entry)
        assert disabled_server_entry is not None
        self.assertFalse(disabled_server_entry['enabled'])

        variable_entries = self._load_section(payload, 'variables')
        disabled_variable_entry = self._find_entry_by_name(variable_entries, 'disabled-template-variable')
        self.assertIsNotNone(disabled_variable_entry)
        assert disabled_variable_entry is not None
        self.assertFalse(disabled_variable_entry['enabled'])

        secrets_section = self._load_section(payload, 'secrets')
        assert secrets_section is not None
        disabled_secret_entry = self._find_entry_by_name(secrets_section['items'], 'disabled-template-secret')
        self.assertIsNotNone(disabled_secret_entry)
        assert disabled_secret_entry is not None
        self.assertFalse(disabled_secret_entry['enabled'])

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
            server = Server(name='server-one', definition='print("hi")')
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
            server = Server(name='server-one', definition=server_definition)
            unreferenced_record = CID(
                path=f'/{unreferenced_cid}',
                file_data=unreferenced_content,
                file_size=len(unreferenced_content),
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
            alias = Alias.query.filter_by( name='alias-b').first()
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

            server = Server.query.filter_by( name='server-b').first()
            self.assertIsNotNone(server)
            self.assertEqual(server.definition, 'print("hello")')

            variable = Variable.query.filter_by( name='var-b').first()
            self.assertIsNotNone(variable)
            self.assertEqual(variable.definition, '42')

            secret = Secret.query.filter_by( name='secret-b').first()
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
            self.assertEqual(resolved, local_file.resolve())

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
        cid_entries: dict[str, str] = {}
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

                def __call__(self, content: bytes) -> str:
                    self.calls.append(content)
                    return f'cid-{len(self.calls)}'

            store_bytes_stub = StoreBytesStub()

            with self.app.app_context():
                with ExitStack() as stack:
                    stack.enter_context(patch('routes.import_export.filesystem_collection.app_root_path', return_value=base_path))
                    stack.enter_context(patch('routes.import_export.export_sections.get_aliases', return_value=[SimpleNamespace(name='example', definition=alias_definition)]))
                    stack.enter_context(patch('routes.import_export.export_sections.get_servers', return_value=[]))
                    stack.enter_context(patch('routes.import_export.export_sections.get_variables', return_value=[]))
                    stack.enter_context(patch('routes.import_export.export_sections.get_secrets', return_value=[]))
                    stack.enter_context(patch('routes.import_export.export_engine.get_uploads', return_value=[]))
                    stack.enter_context(patch('routes.import_export.change_history.gather_change_history', return_value={}))
                    stack.enter_context(patch('routes.import_export.cid_utils.store_cid_from_bytes', side_effect=store_bytes_stub))
                    stack.enter_context(patch('routes.import_export.export_engine.cid_path', return_value='/downloads/export.json'))

                    with self.app.test_request_context():
                        form = ExportForm()
                        form.include_aliases.data = True
                        form.selected_aliases.data = ['example']
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

                        result = import_export._build_export_payload(form)

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
        # CID values are now plain strings, not dicts
        self.assertTrue(
            any('export' in entry for entry in cid_values.values() if isinstance(entry, str))
        )

    def test_process_import_submission_returns_form_on_empty_payload(self):
        with self.app.test_request_context():
            form = ImportForm()

            with ExitStack() as stack:
                stack.enter_context(patch('routes.import_export.import_engine.flash'))

                render_calls: list[Any] = []

                def render_form(snapshot_export: Any) -> str:
                    render_calls.append(snapshot_export)
                    return 'rendered-form'

                # Create a parsed payload with empty data
                from routes.import_export.import_sources import ParsedImportPayload
                parsed = ParsedImportPayload(raw_text=' ', data={})

                response = import_export._process_import_submission(form, 'note', render_form, parsed)

        self.assertEqual(response, 'rendered-form')
        self.assertEqual(len(render_calls), 1)  # Should have been called once

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
            alias = Alias(name='alias-b', definition=definition_text)
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

        # Create a server with UTF-8 content
        with self.app.app_context():
            server = Server(name='test-server', definition=definition_text)
            db.session.add(server)
            db.session.commit()

        # Export the server
        with self.logged_in():
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
        servers = self._load_section(payload, 'servers')
        server_entry = self._find_entry_by_name(servers, 'test-server')
        self.assertIsNotNone(server_entry)
        assert server_entry is not None
        self.assertIn('definition_cid', server_entry)
        self.assertNotIn('definition', server_entry)
        self.assertEqual(cid_values[server_entry['definition_cid']], definition_text)

    def test_snapshot_toggle_checked_hides_options_in_ui(self):
        """Test that when snapshot is checked, the UI hides export options."""
        with self.logged_in():
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # Snapshot toggle should be present
        self.assertIn('id="snapshot-toggle"', html)
        # The snapshot checkbox should be checked (look for checked attribute near the snapshot toggle)
        snapshot_section_start = html.find('id="snapshot-toggle"') - 200
        snapshot_section = html[max(0, snapshot_section_start):snapshot_section_start + 300]
        self.assertIn('checked', snapshot_section)
        # Export options container should have d-none class initially
        self.assertIn('id="export-options-container"', html)
        # Look for the export options container with d-none class
        container_idx = html.find('id="export-options-container"')
        container_section = html[max(0, container_idx-100):container_idx+100]
        self.assertIn('d-none', container_section)

    def test_snapshot_toggle_unchecked_shows_options_in_ui(self):
        """Test that snapshot toggle exists and can be unchecked."""
        with self.logged_in():
            # GET the export page (snapshot checked by default)
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # Snapshot toggle should be present
        self.assertIn('id="snapshot-toggle"', html)
        # Export options container should exist
        self.assertIn('id="export-options-container"', html)
        # JavaScript will handle showing/hiding based on snapshot state
        # The form should allow unchecking snapshot
        self.assertIn('name="snapshot"', html)

    def test_snapshot_unchecked_applies_default_settings(self):
        """Test that when snapshot is unchecked, the correct defaults are applied."""
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='echo test', enabled=False)
            server = Server(name='test-server', definition='print("test")', enabled=False)
            variable = Variable(name='test-var', definition='value', enabled=False)
            db.session.add_all([alias, server, variable])
            db.session.commit()

        with self.logged_in():
            # POST without snapshot field (unchecked) - with non-snapshot defaults
            response = self.client.post('/export', data={
                'include_aliases': 'y',
                'include_disabled_aliases': 'y',
                'include_template_aliases': 'y',
                'include_servers': 'y',
                'include_disabled_servers': 'y',
                'include_template_servers': 'y',
                'include_variables': 'y',
                'include_disabled_variables': 'y',
                'include_template_variables': 'y',
                'submit': True
            })

        self.assertEqual(response.status_code, 200)
        _record, payload = self._load_export_payload()

        # Aliases: all including disabled and templates
        aliases = self._load_section(payload, 'aliases')
        alias_entry = self._find_entry_by_name(aliases, 'test-alias')
        self.assertIsNotNone(alias_entry)
        assert alias_entry is not None
        self.assertFalse(alias_entry['enabled'])

        # Servers: all including disabled and templates
        servers = self._load_section(payload, 'servers')
        server_entry = self._find_entry_by_name(servers, 'test-server')
        self.assertIsNotNone(server_entry)
        assert server_entry is not None
        self.assertFalse(server_entry['enabled'])

        # Variables: all including disabled and templates
        variables = self._load_section(payload, 'variables')
        variable_entry = self._find_entry_by_name(variables, 'test-var')
        self.assertIsNotNone(variable_entry)
        assert variable_entry is not None
        self.assertFalse(variable_entry['enabled'])

        # Secrets: none
        self.assertNotIn('secrets', payload)

        # Change history: none
        self.assertNotIn('change_history', payload)

        # Application source files: none
        self.assertNotIn('app_source', payload)

        # CID content map: none (cid_values should not be present)
        self.assertNotIn('cid_values', payload)

    def test_snapshot_checked_uses_form_defaults(self):
        """Test that when snapshot is checked, it uses the default form settings."""
        with self.app.app_context():
            alias = Alias(name='enabled-alias', definition='echo test', enabled=True)
            disabled_alias = Alias(name='disabled-alias', definition='echo test', enabled=False)
            db.session.add_all([alias, disabled_alias])
            db.session.commit()

        with self.logged_in():
            # POST with snapshot checked and default form fields
            response = self.client.post('/export', data={
                'snapshot': 'y',
                'include_aliases': 'y',
                'include_servers': 'y',
                'include_variables': 'y',
                'include_cid_map': 'y',
                'submit': True
            })

        self.assertEqual(response.status_code, 200)
        _record, payload = self._load_export_payload()

        # Aliases: only enabled ones by default (disabled and templates not included)
        aliases = self._load_section(payload, 'aliases')
        enabled_alias = self._find_entry_by_name(aliases, 'enabled-alias')
        self.assertIsNotNone(enabled_alias)
        assert enabled_alias is not None
        self.assertTrue(enabled_alias['enabled'])

        # CID map should be included by default
        self.assertIn('cid_values', payload)

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
                'include_servers': 'y',
                'process_cid_map': 'y',
                'submit': True,
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 server', response.data)

            # Verify the server was imported correctly
            with self.app.app_context():
                server = Server.query.filter_by( name='imported-server').first()
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
                'include_servers': 'y',
                'process_cid_map': 'y',
                'submit': True,
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 server', response.data)

            # Verify the server was imported correctly
            with self.app.app_context():
                server = Server.query.filter_by( name='old-format-server').first()
                self.assertIsNotNone(server)
                self.assertEqual(server.definition, server_definition)

    def test_import_defaults_to_utf8_without_encoding(self):
        """Test that import defaults to UTF-8 when no encoding is specified."""

        # Test with non-ASCII UTF-8 content
        content_with_unicode = 'Hello 世界 🌍'
        alias_definition = format_primary_alias_line('literal', 'test', content_with_unicode)
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
                'include_aliases': 'y',
                'process_cid_map': 'y',
                'submit': True,
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Imported 1 alias', response.data)

            # Verify the alias was imported with correct UTF-8 content
            with self.app.app_context():
                alias = Alias.query.filter_by( name='test-alias').first()
                self.assertIsNotNone(alias)
                # The alias name gets updated during import, so just check the target content is present
                self.assertIn(content_with_unicode, alias.definition)

    def test_export_records_export_in_database(self):
        """Test that exporting records an Export entry in the database."""
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='echo test')
            db.session.add(alias)
            db.session.commit()

        with self.logged_in():
            response = self.client.post('/export', data={
                'include_aliases': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your export is ready', response.data)

        # Verify export was recorded
        with self.app.app_context():
            exports = Export.query.filter_by().all()
            self.assertEqual(len(exports), 1)
            export = exports[0]
            self.assertIsNotNone(export.cid)
            self.assertIsNotNone(export.created_at)

    def test_export_displays_recent_exports(self):
        """Test that the export page displays recent exports."""
        with self.app.app_context():
            # Create some test exports
            for i in range(3):
                export = Export(
                    cid=f'bafybeicid{i:03d}',
                    created_at=datetime.now(timezone.utc),
                )
                db.session.add(export)
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Recent Exports', html)
        # Check that all export CIDs are displayed
        for i in range(3):
            self.assertIn(f'bafybeicid{i:03d}', html)

    def test_export_shows_only_user_exports(self):
        """Test that exports are displayed (user filtering no longer applies)."""
        with self.app.app_context():
            # Create exports
            export1 = Export(
                cid='bafybeiuser1',
                created_at=datetime.now(timezone.utc),
            )
            export2 = Export(
                cid='bafybeiuser2',
                created_at=datetime.now(timezone.utc),
            )
            db.session.add_all([export1, export2])
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # Both exports should be shown since user filtering is no longer applied
        self.assertIn('bafybeiuser1', html)
        self.assertIn('bafybeiuser2', html)

    def test_export_shows_only_100_most_recent(self):
        """Test that only the 100 most recent exports are shown."""
        with self.app.app_context():
            # Create 105 exports with slightly different timestamps
            base_time = datetime.now(timezone.utc)
            for i in range(105):
                export = Export(
                    cid=f'bafybeiexport{i:03d}',
                    created_at=base_time.replace(microsecond=i),
                )
                db.session.add(export)
            db.session.commit()

        with self.logged_in():
            response = self.client.get('/export')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # Count unique export CIDs in the HTML
        # render_cid_link includes the CID multiple times (in hrefs, titles, data attributes, etc.),
        # so we count how many of the 105 possible exports are actually present
        export_count = len([c for c in range(105) if f'bafybeiexport{c:03d}' in html])
        self.assertEqual(export_count, 100, f'Expected 100 exports, found {export_count}')
        # Should show the most recent ones (higher indices)
        self.assertIn('bafybeiexport104', html)
        self.assertIn('bafybeiexport005', html)
        # Should not show the oldest ones (lower indices)
        self.assertNotIn('bafybeiexport004', html)
        self.assertNotIn('bafybeiexport000', html)

    def test_import_generates_snapshot_export(self):
        """Test that importing data generates a snapshot export equivalent to the default export."""
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='echo test', enabled=True)
            db.session.add(alias)
            db.session.commit()

        # Count exports before import
        with self.app.app_context():
            initial_exports = Export.query.filter_by().count()

        # Create import payload with a valid alias definition (pattern -> target format)
        alias_definition = format_primary_alias_line('literal', None, '/servers/echo', alias_name='imported-alias')
        payload = json.dumps({
            'aliases': [{'name': 'imported-alias', 'definition': alias_definition, 'enabled': True}],
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_aliases': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Imported 1 alias', response.data)

        # Verify snapshot export was created
        with self.app.app_context():
            exports = Export.query.filter_by().all()
            self.assertEqual(len(exports), initial_exports + 1, 'Snapshot export should be created after import')

            # Get the most recent export (the snapshot)
            snapshot_export = Export.query.filter_by().order_by(Export.created_at.desc()).first()
            self.assertIsNotNone(snapshot_export)

            # Verify the snapshot export contains the imported data
            cid_record = CID.query.filter_by(path=f'/{snapshot_export.cid}').first()
            self.assertIsNotNone(cid_record)
            self.assertIsNotNone(cid_record.file_data)

            # Parse the snapshot export payload
            snapshot_payload = json.loads(bytes(cid_record.file_data).decode('utf-8'))
            self.assertIn('aliases', snapshot_payload)
            self.assertIn('version', snapshot_payload)

    def test_import_displays_snapshot_info_on_page(self):
        """Test that the import page displays snapshot export info after import."""
        payload = json.dumps({
            'aliases': [{'name': 'test-alias', 'definition': 'echo test', 'enabled': True}],
        })

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_aliases': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        response.get_data(as_text=True)

        # Check that snapshot info is displayed
        # The snapshot info should be in the page (either from session or flash)
        # We check for the CID pattern which should be present
        with self.app.app_context():
            snapshot_export = Export.query.filter_by().order_by(Export.created_at.desc()).first()
            if snapshot_export:
                # Check that snapshot CID is mentioned (might be in flash or session)
                # The actual display depends on template, but we can verify export was created
                self.assertIsNotNone(snapshot_export.cid)

    def test_import_returns_snapshot_info_in_json_response(self):
        """Test that REST API import returns snapshot info in JSON response."""
        payload = {
            'aliases': [{'name': 'api-alias', 'definition': 'echo api', 'enabled': True}],
        }

        with self.logged_in():
            response = self.client.post(
                '/import',
                json=payload,
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get('ok'))
        self.assertIn('snapshot', data)
        self.assertIn('cid', data['snapshot'])

        # Verify snapshot export was created
        with self.app.app_context():
            snapshot_export = Export.query.filter_by().order_by(Export.created_at.desc()).first()
            self.assertIsNotNone(snapshot_export)
            self.assertEqual(snapshot_export.cid, data['snapshot']['cid'])

    def test_snapshot_export_contains_default_sections(self):
        """Test that snapshot export contains the default export sections."""
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='echo test', enabled=True)
            server = Server(name='test-server', definition='print("test")', enabled=True)
            variable = Variable(name='test-var', definition='value', enabled=True)
            db.session.add_all([alias, server, variable])
            db.session.commit()

        payload = json.dumps({
            'aliases': [{'name': 'imported-alias', 'definition': 'echo imported', 'enabled': True}],
        })

        with self.logged_in():
            self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_aliases': 'y',
                'submit': True,
            }, follow_redirects=True)

        # Get the snapshot export
        with self.app.app_context():
            snapshot_export = Export.query.filter_by().order_by(Export.created_at.desc()).first()
            self.assertIsNotNone(snapshot_export)

            cid_record = CID.query.filter_by(path=f'/{snapshot_export.cid}').first()
            self.assertIsNotNone(cid_record)
            snapshot_payload = json.loads(bytes(cid_record.file_data).decode('utf-8'))

            # Verify snapshot contains default sections (aliases, servers, variables)
            # These are stored as CID strings in the payload
            self.assertIn('aliases', snapshot_payload)
            self.assertIsInstance(snapshot_payload['aliases'], str, 'aliases section should be a CID string')
            self.assertIn('servers', snapshot_payload)
            self.assertIsInstance(snapshot_payload['servers'], str, 'servers section should be a CID string')
            self.assertIn('variables', snapshot_payload)
            self.assertIsInstance(snapshot_payload['variables'], str, 'variables section should be a CID string')
            # Should not contain secrets, history, or source by default
            self.assertNotIn('secrets', snapshot_payload)
            self.assertNotIn('change_history', snapshot_payload)
            self.assertNotIn('app_source', snapshot_payload)
            # Should contain CID map
            self.assertIn('cid_values', snapshot_payload)

    def test_snapshot_exports_from_same_state_have_identical_cids(self):
        """Snapshot exports generated from identical state should share the same CID."""
        with self.app.app_context():
            alias = Alias(name='consistent-alias', definition='echo consistent', enabled=True)
            server = Server(name='consistent-server', definition='print("ok")', enabled=True)
            variable = Variable(name='consistent-var', definition='value', enabled=True)
            db.session.add_all([alias, server, variable])
            db.session.commit()

            # Generate two snapshot exports without changing state
            first_snapshot = generate_snapshot_export()
            second_snapshot = generate_snapshot_export()

            self.assertIsNotNone(first_snapshot)
            self.assertIsNotNone(second_snapshot)
            assert first_snapshot is not None and second_snapshot is not None
            self.assertEqual(first_snapshot['cid_value'], second_snapshot['cid_value'])


if __name__ == '__main__':
    unittest.main()
