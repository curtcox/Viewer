"""Tests for ui_status module."""
import json
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import Variable, db
from ui_status import (
    get_ui_suggestions_info,
    generate_ui_suggestions_label,
)
from ui_manager import (
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
)


class TestUIStatus(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        # Sample valid UIs structure
        self.valid_uis = {
            'aliases': {
                'my-alias': [
                    {'name': 'Dashboard View', 'path': '/dashboard/my-alias'},
                    {'name': 'Graph View', 'path': '/graph/my-alias'},
                ]
            },
            'servers': {
                'my-server': [
                    {'name': 'Debug UI', 'path': '/debug/my-server'},
                ]
            },
            'variables': {
                'my-variable': [
                    {'name': 'Editor', 'path': '/edit/my-variable'},
                    {'name': 'Viewer', 'path': '/view/my-variable'},
                    {'name': 'History', 'path': '/history/my-variable'},
                ]
            }
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_ui_suggestions_info_no_uis(self):
        """Test info when no UIs are defined."""
        info = get_ui_suggestions_info(ENTITY_TYPE_ALIASES, 'my-alias')

        self.assertFalse(info['has_uis'])
        self.assertEqual(info['count'], 0)
        self.assertEqual(info['uis'], [])
        self.assertEqual(info['config_url'], '/variables/uis')
        self.assertEqual(info['label'], 'No additional UIs')

    def test_get_ui_suggestions_info_with_uis(self):
        """Test info when UIs are defined."""
        var = Variable(
            name='uis',
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        info = get_ui_suggestions_info(ENTITY_TYPE_ALIASES, 'my-alias')

        self.assertTrue(info['has_uis'])
        self.assertEqual(info['count'], 2)
        self.assertEqual(len(info['uis']), 2)
        self.assertEqual(info['uis'][0]['name'], 'Dashboard View')
        self.assertEqual(info['uis'][0]['path'], '/dashboard/my-alias')
        self.assertEqual(info['config_url'], '/variables/uis')
        self.assertEqual(info['label'], '2 additional UIs')

    def test_get_ui_suggestions_info_single_ui(self):
        """Test info when exactly one UI is defined."""
        var = Variable(
            name='uis',
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        info = get_ui_suggestions_info(ENTITY_TYPE_SERVERS, 'my-server')

        self.assertTrue(info['has_uis'])
        self.assertEqual(info['count'], 1)
        self.assertEqual(info['label'], '1 additional UI')

    def test_get_ui_suggestions_info_nonexistent_entity(self):
        """Test info for entity without UIs defined."""
        var = Variable(
            name='uis',
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        info = get_ui_suggestions_info(ENTITY_TYPE_ALIASES, 'nonexistent')

        self.assertFalse(info['has_uis'])
        self.assertEqual(info['count'], 0)
        self.assertEqual(info['label'], 'No additional UIs')

    def test_generate_ui_suggestions_label_no_uis(self):
        """Test label when no UIs defined."""
        label = generate_ui_suggestions_label(ENTITY_TYPE_ALIASES, 'my-alias')

        self.assertEqual(label, 'No additional UIs')

    def test_generate_ui_suggestions_label_one_ui(self):
        """Test label for exactly one UI."""
        var = Variable(
            name='uis',
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_ui_suggestions_label(ENTITY_TYPE_SERVERS, 'my-server')

        self.assertEqual(label, '1 additional UI')

    def test_generate_ui_suggestions_label_multiple_uis(self):
        """Test label for multiple UIs."""
        var = Variable(
            name='uis',
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_ui_suggestions_label(ENTITY_TYPE_ALIASES, 'my-alias')
        self.assertEqual(label, '2 additional UIs')

        label = generate_ui_suggestions_label(ENTITY_TYPE_VARIABLES, 'my-variable')
        self.assertEqual(label, '3 additional UIs')


if __name__ == '__main__':
    unittest.main()
