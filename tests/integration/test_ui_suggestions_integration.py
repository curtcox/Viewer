"""Integration tests for UI suggestions feature."""
import json
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import Variable, Alias, Server, db


class TestUIShownOnViews(unittest.TestCase):
    """Test that UI suggestions are displayed on view pages."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Create test entities
        alias = Alias(name='test-alias', definition='literal /test-alias -> /target')
        server = Server(name='test-server', definition='def main(): return "Hello"')
        variable = Variable(name='test-variable', definition='test value')
        db.session.add_all([alias, server, variable])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_alias_view_shows_no_uis_when_none_configured(self):
        """Test alias view page shows 'No additional UIs' when none configured."""
        response = self.client.get('/aliases/test-alias')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('No additional UIs', html)
        self.assertIn('/variables/uis', html)

    def test_server_view_shows_no_uis_when_none_configured(self):
        """Test server view page shows 'No additional UIs' when none configured."""
        response = self.client.get('/servers/test-server')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('No additional UIs', html)
        self.assertIn('/variables/uis', html)

    def test_variable_view_shows_no_uis_when_none_configured(self):
        """Test variable view page shows 'No additional UIs' when none configured."""
        response = self.client.get('/variables/test-variable')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('No additional UIs', html)
        self.assertIn('/variables/uis', html)


class TestUIDisplayedWhenConfigured(unittest.TestCase):
    """Test that configured UIs are displayed on view pages."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Create test entities
        alias = Alias(name='test-alias', definition='literal /test-alias -> /target')
        server = Server(name='test-server', definition='def main(): return "Hello"')
        variable = Variable(name='test-variable', definition='test value')

        # Create UIs configuration
        uis_config = {
            'aliases': {
                'test-alias': [
                    {'name': 'Dashboard', 'path': '/dashboard/test-alias'},
                    {'name': 'Graph View', 'path': '/graph/test-alias'},
                ]
            },
            'servers': {
                'test-server': [
                    {'name': 'Debug UI', 'path': '/debug/test-server'},
                ]
            },
            'variables': {
                'test-variable': [
                    {'name': 'Editor', 'path': '/edit/test-variable'},
                    {'name': 'History', 'path': '/history/test-variable'},
                    {'name': 'Compare', 'path': '/compare/test-variable'},
                ]
            }
        }
        uis_var = Variable(name='uis', definition=json.dumps(uis_config))

        db.session.add_all([alias, server, variable, uis_var])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_alias_view_shows_configured_uis(self):
        """Test alias view page shows configured UIs."""
        response = self.client.get('/aliases/test-alias')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Should show the count
        self.assertIn('2 additional UIs', html)

        # Should show the UI names
        self.assertIn('Dashboard', html)
        self.assertIn('Graph View', html)

        # Should have links to the UIs
        self.assertIn('/dashboard/test-alias', html)
        self.assertIn('/graph/test-alias', html)

    def test_server_view_shows_configured_uis(self):
        """Test server view page shows configured UIs in Details tab."""
        response = self.client.get('/servers/test-server')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Should show the count
        self.assertIn('1 additional UI', html)

        # Should show the UI name
        self.assertIn('Debug UI', html)

        # Should have link to the UI
        self.assertIn('/debug/test-server', html)

    def test_variable_view_shows_configured_uis(self):
        """Test variable view page shows configured UIs."""
        response = self.client.get('/variables/test-variable')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Should show the count
        self.assertIn('3 additional UIs', html)

        # Should show the UI names
        self.assertIn('Editor', html)
        self.assertIn('History', html)
        self.assertIn('Compare', html)

        # Should have links to the UIs
        self.assertIn('/edit/test-variable', html)
        self.assertIn('/history/test-variable', html)
        self.assertIn('/compare/test-variable', html)


if __name__ == '__main__':
    unittest.main()
