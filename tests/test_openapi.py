import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db  # noqa: E402


class TestOpenAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
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

    def test_openapi_schema_includes_entity_management_paths(self):
        response = self.client.get('/openapi.json')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        paths = payload['paths']

        expected_paths = {
            '/aliases': ['get'],
            '/aliases/new': ['get', 'post'],
            '/aliases/{alias_name}': ['get'],
            '/aliases/{alias_name}/edit': ['get', 'post'],
            '/aliases/{alias_name}/enabled': ['post'],
            '/aliases/{alias_name}/delete': ['post'],
            '/aliases/match-preview': ['post'],
            '/servers': ['get'],
            '/servers/new': ['get', 'post'],
            '/servers/{server_name}': ['get'],
            '/servers/{server_name}/edit': ['get', 'post'],
            '/servers/{server_name}/delete': ['post'],
            '/servers/validate-definition': ['post'],
            '/servers/{server_name}/upload-test-page': ['post'],
            '/variables': ['get'],
            '/variables/new': ['get', 'post'],
            '/variables/_/edit': ['get', 'post'],
            '/variables/{variable_name}': ['get'],
            '/variables/{variable_name}/edit': ['get', 'post'],
            '/variables/{variable_name}/delete': ['post'],
            '/secrets': ['get'],
            '/secrets/new': ['get', 'post'],
            '/secrets/_/edit': ['get', 'post'],
            '/secrets/{secret_name}': ['get'],
            '/secrets/{secret_name}/edit': ['get', 'post'],
            '/secrets/{secret_name}/delete': ['post'],
            '/upload': ['get', 'post'],
            '/uploads': ['get'],
        }

        for path, methods in expected_paths.items():
            self.assertIn(path, paths, msg=f'Missing path {path}')
            for method in methods:
                self.assertIn(method, paths[path], msg=f'Missing {method.upper()} for {path}')

        schemas = payload['components']['schemas']
        for schema_name in [
            'AliasFormSubmission',
            'ServerFormSubmission',
            'VariableFormSubmission',
            'VariablesBulkEditFormSubmission',
            'SecretsBulkEditFormSubmission',
            'SecretFormSubmission',
            'DeletionConfirmation',
            'UploadFormSubmission',
        ]:
            self.assertIn(schema_name, schemas, msg=f'Missing schema {schema_name}')

    def test_openapi_schema_describes_multi_format_responses(self):
        response = self.client.get('/openapi.json')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        interactions = payload['paths']['/api/interactions']['post']['responses']['200']['content']
        for mimetype in ['text/html', 'text/plain', 'text/markdown', 'application/xml', 'text/csv']:
            self.assertIn(mimetype, interactions)

        alias_listing = payload['paths']['/aliases']['get']['responses']['200']['content']
        self.assertIn('application/json', alias_listing)
        self.assertIn('application/xml', alias_listing)
        self.assertIn('text/csv', alias_listing)
        alias_json_schema = alias_listing['application/json']['schema']
        self.assertEqual(alias_json_schema['type'], 'array')
        self.assertEqual(
            alias_json_schema['items']['$ref'], '#/components/schemas/AliasRecord'
        )

        server_detail = payload['paths']['/servers/{server_name}']['get']['responses']['200']['content']
        self.assertIn('application/json', server_detail)
        self.assertIn('application/xml', server_detail)
        self.assertIn('text/csv', server_detail)

        schemas = payload['components']['schemas']
        for record_schema in ['AliasRecord', 'ServerRecord', 'VariableRecord', 'SecretRecord']:
            self.assertIn(record_schema, schemas)


if __name__ == '__main__':
    unittest.main()
