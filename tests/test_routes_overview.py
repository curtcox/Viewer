import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')
os.environ.setdefault('TESTING', 'True')

from app import create_app  # noqa: E402
from database import db  # noqa: E402
from models import Alias, Server  # noqa: E402


class RoutesOverviewTestCase(unittest.TestCase):
    """Tests for the routes overview page."""

    def setUp(self):
        self.app = create_app(
            {
                'TESTING': True,
                'WTF_CSRF_ENABLED': False,
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            }
        )
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.user_id = 'user-1'

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self):
        with self.client.session_transaction() as session:
            session['_user_id'] = self.user_id
            session['_fresh'] = True

    def test_requires_login(self):
        response = self.client.get('/routes')
        self.assertEqual(response.status_code, 200)

    def test_lists_builtin_alias_and_server_routes(self):
        alias = Alias(name='shared', target_path='/target', user_id=self.user_id)
        server = Server(
            name='shared',
            definition='def main(request):\n    return "ok"',
            user_id=self.user_id,
        )
        db.session.add_all([alias, server])
        db.session.commit()

        self.login_user()

        response = self.client.get('/routes')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)

        # Built-in route entry should link to its source definition
        self.assertIn('/source/routes/routes_overview.py', page)

        # Alias and server definitions should be linked
        self.assertIn('/aliases/shared', page)
        self.assertIn('/servers/shared', page)

        # Duplicate paths should be highlighted
        self.assertIn('route-duplicate', page)
        self.assertIn('Duplicate</span>', page)

        # Table should avoid zebra-striping and expose fragment highlight support
        self.assertNotIn('table-striped', page)
        self.assertIn('data-original-path', page)
        self.assertIn('route-fragment-highlight', page)

        # Filtering controls and icons should be present
        self.assertIn('id="toggle-builtin"', page)
        self.assertIn('id="toggle-alias"', page)
        self.assertIn('id="toggle-server"', page)
        self.assertIn('fas fa-code me-1', page)
        self.assertIn('fas fa-link me-1', page)
        self.assertIn('fas fa-server me-1', page)
        self.assertIn('fas fa-triangle-exclamation me-1', page)

        # Not found handler should be documented with template details
        self.assertIn('/(any unmatched path)', page)
        self.assertIn('not_found_error', page)
        self.assertIn('Template: templates/404.html', page)
        self.assertIn('route-not-found', page)

    def test_frontend_filtering_orders_exact_partial_and_not_found(self):
        self.login_user()

        response = self.client.get('/routes')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)

        self.assertIn('function normalizeSearchFragment', page)
        self.assertIn('path && path === normalizedSearchLower', page)
        self.assertIn('path.includes(normalizedSearchLower)', page)
        self.assertIn('matchRows.length === 0', page)
        self.assertIn('const rankA = matchSet.has(a) ? 0 : partialSet.has(a) ? 1 : 2;', page)
        self.assertIn('route-partial', page)


if __name__ == '__main__':
    unittest.main()
