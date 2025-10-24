import unittest

from app import app, db
from models import Alias
from db_access import get_alias_by_target_path


class DbAccessAliasIntegrationTests(unittest.TestCase):
    """Test that db_access functions work with the new Alias model structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        self.user_id = "test_user"

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_alias_by_target_path_simple(self):
        """Test finding an alias by target path with simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target",
            user_id=self.user_id
        )
        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/target")

        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_not_found(self):
        """Test when no alias is found for the target path."""
        alias = Alias(
            name="test",
            definition="test -> /other",
            user_id=self.user_id
        )
        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/target")

        self.assertIsNone(result)

    def test_get_alias_by_target_path_wrong_match_type(self):
        """Test when alias has correct target but wrong match type."""
        alias = Alias(
            name="test",
            definition="test* -> /target [glob]",
            user_id=self.user_id
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/target")

        # Should not match because it's glob, not literal
        self.assertIsNone(result)

    def test_get_alias_by_target_path_multiple_aliases(self):
        """Test finding alias when multiple aliases exist."""
        alias1 = Alias(
            name="test1",
            definition="test1 -> /target",
            user_id=self.user_id
        )
        alias2 = Alias(
            name="test2",
            definition="test2 -> /other",
            user_id=self.user_id
        )

        db.session.add_all([alias1, alias2])
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/target")

        self.assertEqual(result, alias1)

    def test_get_alias_by_target_path_parsing_error(self):
        """Test when alias definition cannot be parsed."""
        alias = Alias(
            name="test",
            definition="invalid definition",
            user_id=self.user_id
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/test")

        # Should fallback to name-based path
        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_empty_definition(self):
        """Test when alias has empty definition."""
        alias = Alias(
            name="test",
            definition=None,
            user_id=self.user_id
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/test")

        # Should fallback to name-based path
        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_multi_line_definition(self):
        """Test with multi-line definition (should use primary rule)."""
        definition = """
        docs -> /documentation
          api -> /docs/api/architecture/overview.html
          guide -> /guides/getting-started.html
        """
        alias = Alias(
            name="docs",
            definition=definition.strip(),
            user_id=self.user_id
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/documentation")

        # Should match the primary rule
        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_complex_options(self):
        """Test with complex definition including options."""
        alias = Alias(
            name="blog",
            definition="blog-* -> /posts [glob, ignore-case]",
            user_id=self.user_id
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path(self.user_id, "/posts")

        # Should not match because it's glob, not literal
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()


