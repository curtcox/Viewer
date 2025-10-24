import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from db_access import get_recent_entity_interactions, record_entity_interaction
from identity import ensure_default_user


class TestEntityInteractions(unittest.TestCase):
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

    def test_record_entity_interaction_persists(self):
        record_entity_interaction(
            self.user.id,
            'server',
            'example',
            'save',
            'initial setup',
            'print("hello world")',
        )

        interactions = get_recent_entity_interactions(self.user.id, 'server', 'example')
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].message, 'initial setup')
        self.assertEqual(interactions[0].content, 'print("hello world")')

    def test_api_records_and_returns_updated_history(self):
        record_entity_interaction(
            self.user.id,
            'server',
            'example',
            'save',
            'initial setup',
            'print("hello world")',
        )

        payload = {
            'entity_type': 'server',
            'entity_name': 'example',
            'action': 'ai',
            'message': 'trim trailing spaces',
            'content': 'print("hello world")\n'.strip(),
        }

        response = self.client.post('/api/interactions', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('interactions', data)
        self.assertGreaterEqual(len(data['interactions']), 2)
        latest = data['interactions'][0]
        self.assertEqual(latest['action'], 'ai')
        self.assertEqual(latest['message'], 'trim trailing spaces')

    def test_api_requires_entity_details(self):
        response = self.client.post('/api/interactions', json={'content': 'value'})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()

