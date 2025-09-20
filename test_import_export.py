import json
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from app import create_app, db
from encryption import SECRET_ENCRYPTION_SCHEME, decrypt_secret_value, encrypt_secret_value
from models import Alias, Secret, Server, User, Variable


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
            user = User(
                id=self.user_id,
                email='user@example.com',
                first_name='Test',
                last_name='User',
            )
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _login_patch(self, mock_current_user):
        mock_current_user.id = self.user_id
        mock_current_user.is_authenticated = True
        return mock_current_user

    @contextmanager
    def logged_in(self):
        with ExitStack() as stack:
            route_user = stack.enter_context(patch('routes.import_export.current_user'))
            auth_user = stack.enter_context(patch('auth_providers.current_user'))
            for mock_user in (route_user, auth_user):
                self._login_patch(mock_user)
            yield

    def test_export_includes_selected_collections(self):
        with self.app.app_context():
            alias = Alias(name='alias-one', target_path='/demo', user_id=self.user_id)
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
                'secret_key': 'passphrase',
                'submit': True,
            })

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.data)
        self.assertEqual(payload['version'], 1)
        self.assertIn('generated_at', payload)

        aliases = payload.get('aliases', [])
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]['name'], 'alias-one')

        servers = payload.get('servers', [])
        self.assertEqual(servers[0]['definition'], 'print("hi")')

        variables = payload.get('variables', [])
        self.assertEqual(variables[0]['definition'], 'value')

        secrets_section = payload.get('secrets', {})
        self.assertEqual(secrets_section.get('encryption'), SECRET_ENCRYPTION_SCHEME)
        ciphertext = secrets_section['items'][0]['ciphertext']
        self.assertEqual(decrypt_secret_value(ciphertext, 'passphrase'), 'super-secret')

    def test_import_reports_missing_selected_content(self):
        payload = json.dumps({'aliases': [{'name': 'alias-a', 'target_path': '/path'}]})

        with self.logged_in():
            response = self.client.post('/import', data={
                'import_source': 'text',
                'import_text': payload,
                'include_servers': 'y',
                'submit': True,
            }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No server data found in import file.', response.data)

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
        self.assertIn(b'Invalid decryption key for secrets.', response.data)

    def test_successful_import_creates_entries(self):
        encrypted_secret = encrypt_secret_value('value', 'passphrase')
        payload = json.dumps({
            'aliases': [{'name': 'alias-b', 'target_path': '/demo'}],
            'servers': [{'name': 'server-b', 'definition': 'print("hello")'}],
            'variables': [{'name': 'var-b', 'definition': '42'}],
            'secrets': {
                'encryption': SECRET_ENCRYPTION_SCHEME,
                'items': [
                    {'name': 'secret-b', 'ciphertext': encrypted_secret}
                ],
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
            self.assertEqual(alias.target_path, '/demo')

            server = Server.query.filter_by(user_id=self.user_id, name='server-b').first()
            self.assertIsNotNone(server)
            self.assertEqual(server.definition, 'print("hello")')

            variable = Variable.query.filter_by(user_id=self.user_id, name='var-b').first()
            self.assertIsNotNone(variable)
            self.assertEqual(variable.definition, '42')

            secret = Secret.query.filter_by(user_id=self.user_id, name='secret-b').first()
            self.assertIsNotNone(secret)
            self.assertEqual(secret.definition, 'value')


if __name__ == '__main__':
    unittest.main()
