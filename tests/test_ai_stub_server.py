import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from ai_defaults import ensure_ai_stub_for_user
from db_access import get_alias_by_name, get_server_by_name
from identity import ensure_default_user
from models import Alias, Server


class TestAiStubServer(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = ensure_default_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_ai_stub_resources_created(self):
        alias = get_alias_by_name(self.user.id, 'ai')
        server = get_server_by_name(self.user.id, 'ai_stub')
        self.assertIsInstance(alias, Alias)
        self.assertIsInstance(server, Server)

    def test_ai_alias_created_when_missing(self):
        alias = get_alias_by_name(self.user.id, 'ai')
        self.assertIsNotNone(alias)
        db.session.delete(alias)
        db.session.commit()

        changed = ensure_ai_stub_for_user(self.user.id)
        self.assertTrue(changed)

        recreated = get_alias_by_name(self.user.id, 'ai')
        self.assertIsInstance(recreated, Alias)
        self.assertIn('ai -> /ai_stub', recreated.definition)

    def test_ai_alias_preserved_when_already_defined(self):
        alias = get_alias_by_name(self.user.id, 'ai')
        self.assertIsNotNone(alias)
        alias.definition = 'ai -> /custom-target'
        db.session.add(alias)
        db.session.commit()

        changed = ensure_ai_stub_for_user(self.user.id)
        self.assertFalse(changed)

        refreshed = get_alias_by_name(self.user.id, 'ai')
        self.assertEqual(refreshed.definition.strip(), 'ai -> /custom-target')

    def test_ai_alias_definition_can_be_updated_by_user(self):
        alias = get_alias_by_name(self.user.id, 'ai')
        self.assertIsNotNone(alias)
        alias.definition = 'ai -> /custom-target'
        db.session.add(alias)
        db.session.commit()

        fetched = get_alias_by_name(self.user.id, 'ai')
        self.assertEqual(fetched.definition.strip(), 'ai -> /custom-target')

    def test_ai_stub_invocation_returns_expected_payload(self):
        payload = {
            'request_text': 'Add this line',
            'original_text': 'Existing text',
            'target_label': 'CID content',
            'context_data': {'form': 'upload_text'},
            'form_summary': {'text_content': 'Existing text'},
        }

        initial_response = self.client.post('/ai', json=payload, follow_redirects=False)
        self.assertEqual(initial_response.status_code, 307)
        self.assertEqual(initial_response.headers['Location'], '/ai_stub')

        response = self.client.post('/ai', json=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'updated_text': 'Existing text\nAdd this line',
                'message': 'OK I changed CID content by Add this line',
                'context_summary': 'Context keys: form\nForm fields captured: text_content',
            },
        )

    def test_custom_ai_server_takes_precedence(self):
        # Remove the default alias so the custom server handles /ai directly
        alias = get_alias_by_name(self.user.id, 'ai')
        if alias:
            db.session.delete(alias)
            db.session.commit()

        custom_definition = """
import json

def main():
    return {
        'output': json.dumps({
            'updated_text': 'Custom output',
            'message': 'Handled by custom AI server',
            'context_summary': ''
        }),
        'content_type': 'application/json',
    }
"""
        server = Server(name='ai', definition=custom_definition, user_id=self.user.id)
        db.session.add(server)
        db.session.commit()

        payload = {'request_text': '', 'original_text': 'Ignored'}
        response = self.client.post('/ai', json=payload, follow_redirects=True)
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'updated_text': 'Custom output',
                'message': 'Handled by custom AI server',
                'context_summary': '',
            },
        )


if __name__ == '__main__':
    unittest.main()
