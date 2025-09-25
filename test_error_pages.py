import unittest

from app import create_app
from database import db
from routes.core import internal_error


class TestInternalServerErrorPage(unittest.TestCase):
    """Tests for the customized 500 error page with stack trace links."""

    def setUp(self):
        self.app = create_app(
            {
                'TESTING': False,
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'WTF_CSRF_ENABLED': False,
            }
        )
        self.app.config['PROPAGATE_EXCEPTIONS'] = False

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_error_page_includes_source_links(self):
        with self.app.test_request_context('/broken'):
            try:
                raise RuntimeError('Intentional failure for testing')
            except RuntimeError as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)

        body = response
        self.assertIn('RuntimeError', body)
        self.assertIn('Intentional failure for testing', body)
        self.assertIn('href="/source/test_error_pages.py"', body)
        self.assertIn('<code>test_error_pages.py</code>', body)

