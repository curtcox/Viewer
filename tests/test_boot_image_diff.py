"""Tests for boot image vs database difference detection."""

import json
import unittest
from io import StringIO
from unittest.mock import patch

from app import create_app, db
from boot_image_diff import (
    BootImageDiffResult,
    compare_boot_image_to_db,
    print_boot_image_differences,
)
from cid_utils import generate_cid
from db_access import create_cid_record, save_entity
from models import Alias, Secret, Server, Variable


class TestBootImageDiff(unittest.TestCase):
    """Tests for boot image difference detection."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_compare_no_differences_empty_db(self):
        """Test comparison when DB is empty (new entities will be created)."""
        with self.app.app_context():
            # Create aliases section content
            aliases_data = [
                {'name': 'new-alias', 'definition': '/new-alias -> /target'}
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            payload = {
                'version': 6,
                'aliases': aliases_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            # No differences since alias doesn't exist in DB yet
            self.assertFalse(result.has_differences)
            self.assertEqual(result.aliases_different, [])

    def test_compare_alias_different_definition(self):
        """Test that different alias definitions are detected."""
        with self.app.app_context():
            # Create existing alias in DB
            alias = Alias(
                name='test-alias',
                definition='/test-alias -> /old-target',
                enabled=True,
            )
            save_entity(alias)

            # Create aliases section content with different definition
            aliases_data = [
                {'name': 'test-alias', 'definition': '/test-alias -> /new-target'}
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            payload = {
                'version': 6,
                'aliases': aliases_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-alias', result.aliases_different)

    def test_compare_alias_same_definition(self):
        """Test that identical alias definitions are not reported."""
        with self.app.app_context():
            # Create existing alias in DB
            alias = Alias(
                name='test-alias',
                definition='/test-alias -> /target',
                enabled=True,
            )
            save_entity(alias)

            # Create aliases section content with same definition
            aliases_data = [
                {'name': 'test-alias', 'definition': '/test-alias -> /target'}
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            payload = {
                'version': 6,
                'aliases': aliases_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertFalse(result.has_differences)
            self.assertEqual(result.aliases_different, [])

    def test_compare_server_different_definition(self):
        """Test that different server definitions are detected."""
        with self.app.app_context():
            # Create existing server in DB
            server = Server(
                name='test-server',
                definition='echo "old"',
                enabled=True,
            )
            save_entity(server)

            # Create servers section content with different definition
            servers_data = [
                {'name': 'test-server', 'definition': 'echo "new"'}
            ]
            servers_content = json.dumps(servers_data).encode('utf-8')
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            payload = {
                'version': 6,
                'servers': servers_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-server', result.servers_different)

    def test_compare_variable_different_definition(self):
        """Test that different variable definitions are detected."""
        with self.app.app_context():
            # Create existing variable in DB
            variable = Variable(
                name='test-var',
                definition='old-value',
                enabled=True,
            )
            save_entity(variable)

            # Create variables section content with different definition
            variables_data = [
                {'name': 'test-var', 'definition': 'new-value'}
            ]
            variables_content = json.dumps(variables_data).encode('utf-8')
            variables_cid = generate_cid(variables_content)
            create_cid_record(variables_cid, variables_content)

            payload = {
                'version': 6,
                'variables': variables_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-var', result.variables_different)

    def test_compare_secret_different_enabled(self):
        """Test that different secret enabled flags are detected."""
        with self.app.app_context():
            # Create existing secret in DB
            secret = Secret(
                name='test-secret',
                definition='secret-value',
                enabled=True,
            )
            save_entity(secret)

            # Create secrets section content with different enabled flag
            secrets_data = [
                {'name': 'test-secret', 'ciphertext': 'encrypted', 'enabled': False}
            ]
            secrets_content = json.dumps(secrets_data).encode('utf-8')
            secrets_cid = generate_cid(secrets_content)
            create_cid_record(secrets_cid, secrets_content)

            payload = {
                'version': 6,
                'secrets': secrets_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-secret', result.secrets_different)

    def test_compare_multiple_entity_types(self):
        """Test that differences in multiple entity types are detected."""
        with self.app.app_context():
            # Create existing entities in DB
            alias = Alias(
                name='test-alias',
                definition='/test-alias -> /old',
                enabled=True,
            )
            save_entity(alias)

            server = Server(
                name='test-server',
                definition='echo "old"',
                enabled=True,
            )
            save_entity(server)

            # Create section contents with different definitions
            aliases_data = [
                {'name': 'test-alias', 'definition': '/test-alias -> /new'}
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            servers_data = [
                {'name': 'test-server', 'definition': 'echo "new"'}
            ]
            servers_content = json.dumps(servers_data).encode('utf-8')
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            payload = {
                'version': 6,
                'aliases': aliases_cid,
                'servers': servers_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-alias', result.aliases_different)
            self.assertIn('test-server', result.servers_different)

    def test_compare_enabled_flag_difference(self):
        """Test that enabled flag differences are detected for aliases."""
        with self.app.app_context():
            # Create existing alias in DB with enabled=True
            alias = Alias(
                name='test-alias',
                definition='/test-alias -> /target',
                enabled=True,
            )
            save_entity(alias)

            # Create aliases section content with same definition but enabled=False
            aliases_data = [
                {'name': 'test-alias', 'definition': '/test-alias -> /target', 'enabled': False}
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            payload = {
                'version': 6,
                'aliases': aliases_cid,
            }

            result = compare_boot_image_to_db(payload, {})

            self.assertTrue(result.has_differences)
            self.assertIn('test-alias', result.aliases_different)


class TestPrintBootImageDifferences(unittest.TestCase):
    """Tests for printing boot image differences."""

    def test_print_no_differences(self):
        """Test that nothing is printed when there are no differences."""
        result = BootImageDiffResult()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertEqual(output, '')

    def test_print_alias_differences(self):
        """Test that alias differences are printed."""
        result = BootImageDiffResult(
            aliases_different=['alias-a', 'alias-b'],
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertIn('WARNING', output)
        self.assertIn('Aliases', output)
        self.assertIn('alias-a', output)
        self.assertIn('alias-b', output)

    def test_print_server_differences(self):
        """Test that server differences are printed."""
        result = BootImageDiffResult(
            servers_different=['server-x'],
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertIn('WARNING', output)
        self.assertIn('Servers', output)
        self.assertIn('server-x', output)

    def test_print_variable_differences(self):
        """Test that variable differences are printed."""
        result = BootImageDiffResult(
            variables_different=['var1', 'var2', 'var3'],
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertIn('WARNING', output)
        self.assertIn('Variables', output)
        self.assertIn('var1', output)
        self.assertIn('var2', output)
        self.assertIn('var3', output)

    def test_print_secret_differences(self):
        """Test that secret differences are printed."""
        result = BootImageDiffResult(
            secrets_different=['secret1'],
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertIn('WARNING', output)
        self.assertIn('Secrets', output)
        self.assertIn('secret1', output)

    def test_print_all_differences(self):
        """Test that all types of differences are printed."""
        result = BootImageDiffResult(
            aliases_different=['alias1'],
            servers_different=['server1'],
            variables_different=['var1'],
            secrets_different=['secret1'],
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_boot_image_differences(result)
            output = mock_stdout.getvalue()

        self.assertIn('Aliases', output)
        self.assertIn('Servers', output)
        self.assertIn('Variables', output)
        self.assertIn('Secrets', output)
        self.assertIn('boot image values will overwrite', output)


class TestBootImageDiffResult(unittest.TestCase):
    """Tests for BootImageDiffResult dataclass."""

    def test_has_differences_false_when_empty(self):
        """Test has_differences is False when no differences."""
        result = BootImageDiffResult()
        self.assertFalse(result.has_differences)

    def test_has_differences_true_with_aliases(self):
        """Test has_differences is True with alias differences."""
        result = BootImageDiffResult(aliases_different=['a'])
        self.assertTrue(result.has_differences)

    def test_has_differences_true_with_servers(self):
        """Test has_differences is True with server differences."""
        result = BootImageDiffResult(servers_different=['s'])
        self.assertTrue(result.has_differences)

    def test_has_differences_true_with_variables(self):
        """Test has_differences is True with variable differences."""
        result = BootImageDiffResult(variables_different=['v'])
        self.assertTrue(result.has_differences)

    def test_has_differences_true_with_secrets(self):
        """Test has_differences is True with secret differences."""
        result = BootImageDiffResult(secrets_different=['s'])
        self.assertTrue(result.has_differences)


if __name__ == '__main__':
    unittest.main()
