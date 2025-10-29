import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app, db
from css_defaults import ensure_css_alias_for_user
from db_access import get_alias_by_name
from identity import ensure_default_user
from upload_templates import get_upload_templates


class TestCssAliasDefaults(unittest.TestCase):
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

    def test_css_alias_created_with_expected_definition(self):
        alias = get_alias_by_name(self.user.id, 'CSS')
        self.assertIsNotNone(alias)
        lines = [line.strip() for line in alias.definition.splitlines() if line.strip()]
        self.assertGreaterEqual(len(lines), 4)
        self.assertEqual(lines[0], 'css/custom.css -> /css/default')
        self.assertIn('css/lightmode -> /static/css/custom.css', lines)
        self.assertIn('css/darkmode -> /static/css/custom.css', lines)

    def test_css_alias_created_when_missing(self):
        alias = get_alias_by_name(self.user.id, 'CSS')
        self.assertIsNotNone(alias)
        db.session.delete(alias)
        db.session.commit()

        changed = ensure_css_alias_for_user(self.user.id)
        self.assertTrue(changed)

        recreated = get_alias_by_name(self.user.id, 'CSS')
        self.assertIsNotNone(recreated)
        self.assertIn('css/custom.css -> /css/default', recreated.definition)

    def test_css_alias_preserved_when_already_defined(self):
        alias = get_alias_by_name(self.user.id, 'CSS')
        self.assertIsNotNone(alias)
        alias.definition = 'css/custom.css -> /css/darkmode'
        db.session.add(alias)
        db.session.commit()

        changed = ensure_css_alias_for_user(self.user.id)
        self.assertFalse(changed)

        refreshed = get_alias_by_name(self.user.id, 'CSS')
        self.assertEqual(refreshed.definition.strip(), 'css/custom.css -> /css/darkmode')

    def test_css_alias_definition_can_be_updated_by_user(self):
        alias = get_alias_by_name(self.user.id, 'CSS')
        self.assertIsNotNone(alias)
        alias.definition = 'css/custom.css -> /css/darkmode'
        db.session.add(alias)
        db.session.commit()

        fetched = get_alias_by_name(self.user.id, 'CSS')
        self.assertEqual(fetched.definition.strip(), 'css/custom.css -> /css/darkmode')

    def test_css_alias_redirect_chain(self):
        first = self.client.get('/css/custom.css', follow_redirects=False)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first.headers['Location'], '/css/default')

        second = self.client.get(first.headers['Location'], follow_redirects=False)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second.headers['Location'], '/css/lightmode')

        third = self.client.get(second.headers['Location'], follow_redirects=False)
        self.assertEqual(third.status_code, 302)
        self.assertEqual(third.headers['Location'], '/static/css/custom.css')

        final = self.client.get(third.headers['Location'], follow_redirects=False)
        self.assertEqual(final.status_code, 200)
        self.assertIn(b'/* Custom styles for Viewer */', final.data)

    def test_css_upload_templates_available(self):
        template_ids = {template['id'] for template in get_upload_templates()}
        self.assertIn('css-light-mode', template_ids)
        self.assertIn('css-dark-mode', template_ids)


if __name__ == '__main__':
    unittest.main()
