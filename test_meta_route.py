import json
import unittest

from app import app, db
from models import CID, ServerInvocation, User


class TestMetaRoute(unittest.TestCase):
    """Tests for the /meta diagnostic route."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_test_user(self):
        user = User(
            id='user-123',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def _create_cid(self, cid_value: str, content: bytes = b'test', user: User = None):
        if user is None:
            user = self._create_test_user()
        record = CID(
            path=f'/{cid_value}',
            file_data=content,
            file_size=len(content),
            uploaded_by_user_id=user.id,
        )
        db.session.add(record)
        db.session.commit()
        return record

    def test_meta_route_reports_route_information(self):
        with self.app.app_context():
            response = self.client.get('/meta/privacy')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['path'], '/privacy')
            self.assertEqual(data['status_code'], 200)
            self.assertIn('resolution', data)
            self.assertEqual(data['resolution']['type'], 'route')
            self.assertEqual(data['resolution']['endpoint'], 'main.privacy')
            self.assertIn('/source/routes/core.py', data['source_links'])

    def test_meta_route_returns_404_for_unknown_path(self):
        with self.app.app_context():
            response = self.client.get('/meta/does-not-exist')
            self.assertEqual(response.status_code, 404)

            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Path not found')

    def test_meta_route_includes_template_source_links(self):
        with self.app.app_context():
            response = self.client.get('/meta/settings')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertIn('/source/templates/settings.html', data['source_links'])

    def test_meta_route_includes_server_event_links_for_cid(self):
        with self.app.app_context():
            user = self._create_test_user()
            self._create_cid('cid-result', b'result', user)

            related_cids = ['cid-inv', 'cid-request', 'cid-servers', 'cid-vars', 'cid-secrets']
            for cid in related_cids:
                self._create_cid(cid, b'extra', user)

            invocation = ServerInvocation(
                user_id=user.id,
                server_name='demo-server',
                result_cid='cid-result',
                invocation_cid='cid-inv',
                request_details_cid='cid-request',
                servers_cid='cid-servers',
                variables_cid='cid-vars',
                secrets_cid='cid-secrets',
            )
            db.session.add(invocation)
            db.session.commit()

            response = self.client.get('/meta/cid-result')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['resolution']['type'], 'cid')
            self.assertEqual(data['resolution']['cid'], 'cid-result')
            self.assertIn('server_events', data)

            events = data['server_events']
            self.assertTrue(any(event['server_name'] == 'demo-server' for event in events))

            first_event = events[0]
            self.assertIn('/server_events', first_event['event_page'])

            expected_links = {f'/meta/{cid}' for cid in ['cid-result'] + related_cids}
            self.assertTrue(expected_links.issubset(set(first_event['related_cid_meta_links'])))

            self.assertIn('/source/cid_utils.py', data['source_links'])
            self.assertIn('/source/server_execution.py', data['source_links'])

    def test_meta_route_html_format_renders_links(self):
        with self.app.app_context():
            response = self.client.get('/meta/settings.html')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/html')

            body = response.data.decode('utf-8')
            self.assertIn('<a href="/settings"><code>/settings</code></a>', body)
            self.assertIn('<a href="/source/templates/settings.html"><code>/source/templates/settings.html</code></a>', body)


if __name__ == '__main__':
    unittest.main()
