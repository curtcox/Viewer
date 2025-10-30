import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db  # noqa: E402
from identity import ensure_default_user  # noqa: E402


class TestOpenAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        ensure_default_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_openapi_schema_describes_interactions_endpoint(self):
        response = self.client.get('/openapi.json')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(payload['openapi'], '3.0.3')
        self.assertIn('/api/interactions', payload['paths'])

        post_definition = payload['paths']['/api/interactions']['post']
        self.assertEqual(post_definition['summary'], 'Record entity interaction')
        self.assertIn('requestBody', post_definition)
        self.assertIn('responses', post_definition)
        self.assertIn('200', post_definition['responses'])
        self.assertIn('400', post_definition['responses'])

        request_schema = post_definition['requestBody']['content']['application/json']['schema']
        self.assertEqual(request_schema['$ref'], '#/components/schemas/InteractionRequest')

        servers = payload.get('servers', [])
        self.assertTrue(servers)
        self.assertEqual(servers[0]['url'], 'http://localhost')

    def test_swagger_ui_page_includes_bundle(self):
        response = self.client.get('/openapi')
        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)
        self.assertIn('SwaggerUIBundle', html)
        self.assertIn('/openapi.json', html)


if __name__ == '__main__':
    unittest.main()
