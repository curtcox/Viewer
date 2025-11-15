"""Tests for db_access.uploads module."""
import json
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import Variable, CID, db
from db_access.uploads import get_user_template_uploads


class TestDbAccessUploads(unittest.TestCase):
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_user_template_uploads_no_templates(self):
        """Test getting upload templates when none exist."""
        templates = get_user_template_uploads(self.user_id)

        self.assertEqual(len(templates), 0)

    def test_get_user_template_uploads_with_templates(self):
        """Test getting upload templates with direct content."""
        templates_config = {
            'aliases': {},
            'servers': {},
            'variables': {},
            'secrets': {},
            'uploads': {
                'hello': {
                    'name': 'Hello World',
                    'content': 'Hello, World!'
                },
                'json_sample': {
                    'name': 'JSON Sample',
                    'content': '{"key": "value"}'
                }
            }
        }

        var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_user_template_uploads(self.user_id)

        self.assertEqual(len(templates), 2)

        # Check first template
        hello_template = next((t for t in templates if t['id'] == 'hello'), None)
        self.assertIsNotNone(hello_template)
        self.assertEqual(hello_template['name'], 'Hello World')
        self.assertEqual(hello_template['content'], 'Hello, World!')

        # Check second template
        json_template = next((t for t in templates if t['id'] == 'json_sample'), None)
        self.assertIsNotNone(json_template)
        self.assertEqual(json_template['name'], 'JSON Sample')
        self.assertEqual(json_template['content'], '{"key": "value"}')

    def test_get_user_template_uploads_with_cid_content(self):
        """Test getting upload templates with CID-referenced content."""
        # Create CID record with content
        content_data = b'This is template content from CID'
        cid_record = CID(
            path='/UPLOADTEMPLATECID',
            file_data=content_data,
            file_size=len(content_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        templates_config = {
            'aliases': {},
            'servers': {},
            'variables': {},
            'secrets': {},
            'uploads': {
                'cid_template': {
                    'name': 'CID Template',
                    'content_cid': 'UPLOADTEMPLATECID'
                }
            }
        }

        var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_user_template_uploads(self.user_id)

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]['id'], 'cid_template')
        self.assertEqual(templates[0]['name'], 'CID Template')
        self.assertEqual(templates[0]['content'], 'This is template content from CID')

    def test_get_user_template_uploads_sorted_by_name(self):
        """Test that upload templates are sorted by name."""
        templates_config = {
            'aliases': {},
            'servers': {},
            'variables': {},
            'secrets': {},
            'uploads': {
                'zebra': {
                    'name': 'Zebra Template',
                    'content': 'zzz'
                },
                'alpha': {
                    'name': 'Alpha Template',
                    'content': 'aaa'
                },
                'beta': {
                    'name': 'Beta Template',
                    'content': 'bbb'
                }
            }
        }

        var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_user_template_uploads(self.user_id)

        self.assertEqual(len(templates), 3)
        self.assertEqual(templates[0]['name'], 'Alpha Template')
        self.assertEqual(templates[1]['name'], 'Beta Template')
        self.assertEqual(templates[2]['name'], 'Zebra Template')

    def test_get_user_template_uploads_empty_content(self):
        """Test handling of templates with no content."""
        templates_config = {
            'aliases': {},
            'servers': {},
            'variables': {},
            'secrets': {},
            'uploads': {
                'empty': {
                    'name': 'Empty Template'
                    # No content field
                }
            }
        }

        var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_user_template_uploads(self.user_id)

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]['id'], 'empty')
        self.assertEqual(templates[0]['name'], 'Empty Template')
        self.assertEqual(templates[0]['content'], '')


if __name__ == '__main__':
    unittest.main()
