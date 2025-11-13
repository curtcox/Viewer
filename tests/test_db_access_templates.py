"""Tests for template retrieval through database access layer."""
import json
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import Variable, db
from db_access.aliases import get_user_template_aliases
from db_access.servers import get_user_template_servers
from db_access.variables import get_user_template_variables
from db_access.secrets import get_user_template_secrets


class TestDBAccessTemplates(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        self.user_id = 'testuser'

        # Sample valid templates structure
        self.valid_templates = {
            'aliases': {
                'alias1': {
                    'name': 'Test Alias 1',
                },
                'alias2': {
                    'name': 'Test Alias 2',
                }
            },
            'servers': {
                'server1': {
                    'name': 'Test Server 1',
                }
            },
            'variables': {
                'var1': {
                    'name': 'Test Variable 1',
                }
            },
            'secrets': {
                'secret1': {
                    'name': 'Test Secret 1',
                },
                'secret2': {
                    'name': 'Test Secret 2',
                }
            }
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_user_template_aliases_empty(self):
        """Test getting template aliases when no templates exist."""
        aliases = get_user_template_aliases(self.user_id)

        self.assertEqual(len(aliases), 0)

    def test_get_user_template_aliases_with_templates(self):
        """Test getting template aliases from templates variable."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        aliases = get_user_template_aliases(self.user_id)

        self.assertEqual(len(aliases), 2)
        self.assertTrue(all(a.template for a in aliases))
        self.assertEqual(aliases[0].user_id, self.user_id)
        # Should be sorted by name
        names = [a.name for a in aliases]
        self.assertEqual(names, sorted(names))

    def test_get_user_template_servers_empty(self):
        """Test getting template servers when no templates exist."""
        servers = get_user_template_servers(self.user_id)

        self.assertEqual(len(servers), 0)

    def test_get_user_template_servers_with_templates(self):
        """Test getting template servers from templates variable."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        servers = get_user_template_servers(self.user_id)

        self.assertEqual(len(servers), 1)
        self.assertTrue(all(s.template for s in servers))
        self.assertEqual(servers[0].name, 'Test Server 1')
        self.assertEqual(servers[0].user_id, self.user_id)

    def test_get_user_template_variables_empty(self):
        """Test getting template variables when no templates exist."""
        variables = get_user_template_variables(self.user_id)

        self.assertEqual(len(variables), 0)

    def test_get_user_template_variables_with_templates(self):
        """Test getting template variables from templates variable."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        variables = get_user_template_variables(self.user_id)

        self.assertEqual(len(variables), 1)
        self.assertTrue(all(v.template for v in variables))
        self.assertEqual(variables[0].name, 'Test Variable 1')
        self.assertEqual(variables[0].user_id, self.user_id)

    def test_get_user_template_secrets_empty(self):
        """Test getting template secrets when no templates exist."""
        secrets = get_user_template_secrets(self.user_id)

        self.assertEqual(len(secrets), 0)

    def test_get_user_template_secrets_with_templates(self):
        """Test getting template secrets from templates variable."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        secrets = get_user_template_secrets(self.user_id)

        self.assertEqual(len(secrets), 2)
        self.assertTrue(all(s.template for s in secrets))
        self.assertEqual(secrets[0].user_id, self.user_id)
        # Should be sorted by name
        names = [s.name for s in secrets]
        self.assertEqual(names, sorted(names))

    def test_template_objects_have_no_id(self):
        """Test that template objects have None as ID since they're not in DB."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        aliases = get_user_template_aliases(self.user_id)
        servers = get_user_template_servers(self.user_id)

        self.assertTrue(all(a.id is None for a in aliases))
        self.assertTrue(all(s.id is None for s in servers))

    def test_template_objects_marked_as_template(self):
        """Test that all template objects are marked with template=True."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        aliases = get_user_template_aliases(self.user_id)
        servers = get_user_template_servers(self.user_id)
        variables = get_user_template_variables(self.user_id)
        secrets = get_user_template_secrets(self.user_id)

        self.assertTrue(all(a.template for a in aliases))
        self.assertTrue(all(s.template for s in servers))
        self.assertTrue(all(v.template for v in variables))
        self.assertTrue(all(s.template for s in secrets))

    def test_invalid_templates_variable(self):
        """Test handling of invalid templates variable."""
        var = Variable(
            name='templates',
            definition='invalid json {{{',
            user_id=self.user_id
        )
        db.session.add(var)
        db.session.commit()

        aliases = get_user_template_aliases(self.user_id)
        servers = get_user_template_servers(self.user_id)

        # Should return empty lists on invalid JSON
        self.assertEqual(len(aliases), 0)
        self.assertEqual(len(servers), 0)


if __name__ == '__main__':
    unittest.main()
