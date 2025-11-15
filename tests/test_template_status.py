"""Tests for template_status module."""
import json
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import Variable, db
from template_status import (
    generate_template_status_label,
    get_template_link_info,
)


class TestTemplateStatus(unittest.TestCase):
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
                'template1': {
                    'name': 'Template Alias 1',
                },
                'template2': {
                    'name': 'Template Alias 2',
                }
            },
            'servers': {
                'server1': {
                    'name': 'Template Server 1',
                }
            },
            'variables': {},
            'secrets': {}
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_generate_label_no_templates(self):
        """Test label generation when no templates exist."""
        label = generate_template_status_label(self.user_id)

        self.assertEqual(label, "No templates")

    def test_generate_label_single_template(self):
        """Test label generation with single template."""
        single_template = {
            'aliases': {
                'template1': {'name': 'Only One'}
            },
            'servers': {},
            'variables': {},
            'secrets': {}
        }

        var = Variable(
            name='templates',
            definition=json.dumps(single_template),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_template_status_label(self.user_id)

        self.assertEqual(label, "1 template")

    def test_generate_label_multiple_templates(self):
        """Test label generation with multiple templates."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_template_status_label(self.user_id)

        self.assertEqual(label, "3 templates")

    def test_generate_label_for_specific_type(self):
        """Test label generation for specific entity type."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_template_status_label(self.user_id, 'aliases')

        self.assertEqual(label, "2 templates")

    def test_generate_label_for_type_with_no_templates(self):
        """Test label generation for type with no templates."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_template_status_label(self.user_id, 'variables')

        self.assertEqual(label, "No templates")

    def test_generate_label_for_type_single(self):
        """Test label generation for type with single template."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        label = generate_template_status_label(self.user_id, 'servers')

        self.assertEqual(label, "1 template")

    def test_generate_label_empty_user_id(self):
        """Test label generation with empty user ID."""
        label = generate_template_status_label('')

        self.assertEqual(label, "No templates")

    def test_get_link_info_no_templates(self):
        """Test link info generation with no templates."""
        info = get_template_link_info(self.user_id)

        self.assertEqual(info['label'], "No templates")
        self.assertEqual(info['url'], "/variables/templates")
        self.assertEqual(info['css_class'], "template-status-empty")

    def test_get_link_info_with_templates(self):
        """Test link info generation with templates."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        info = get_template_link_info(self.user_id)

        self.assertEqual(info['label'], "3 templates")
        self.assertEqual(info['url'], "/variables/templates")
        self.assertEqual(info['css_class'], "template-status-active")

    def test_get_link_info_with_type_filter(self):
        """Test link info generation with entity type filter."""
        var = Variable(
            name='templates',
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        info = get_template_link_info(self.user_id, 'aliases')

        self.assertEqual(info['label'], "2 templates")
        self.assertEqual(info['url'], "/variables/templates?type=aliases")
        self.assertEqual(info['css_class'], "template-status-active")

    def test_get_link_info_empty_user_id(self):
        """Test link info generation with empty user ID."""
        info = get_template_link_info('')

        self.assertEqual(info['label'], "No templates")
        self.assertEqual(info['url'], "/variables/templates")
        self.assertEqual(info['css_class'], "template-status-empty")


if __name__ == '__main__':
    unittest.main()
