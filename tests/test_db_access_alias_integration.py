import unittest

from app import app, db
from models import Alias
from db_access import get_alias_by_target_path


class TestDbAccessAliasIntegration(unittest.TestCase):
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

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_alias_by_target_path_simple(self):
        """Test finding an alias by target path with simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target"
        )
        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/target")

        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_not_found(self):
        """Test when no alias is found for the target path."""
        alias = Alias(
            name="test",
            definition="test -> /other"
        )
        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/target")

        self.assertIsNone(result)

    def test_get_alias_by_target_path_wrong_match_type(self):
        """Test when alias has correct target but wrong match type."""
        alias = Alias(
            name="test",
            definition="test* -> /target [glob]"
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/target")

        # Should not match because it's glob, not literal
        self.assertIsNone(result)

    def test_get_alias_by_target_path_multiple_aliases(self):
        """Test finding alias when multiple aliases exist."""
        alias1 = Alias(
            name="test1",
            definition="test1 -> /target"
        )
        alias2 = Alias(
            name="test2",
            definition="test2 -> /other"
        )

        db.session.add_all([alias1, alias2])
        db.session.commit()

        result = get_alias_by_target_path("/target")

        self.assertEqual(result, alias1)

    def test_get_alias_by_target_path_parsing_error(self):
        """Test when alias definition cannot be parsed."""
        alias = Alias(
            name="test",
            definition="invalid definition"
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/test")

        # Should fallback to name-based path
        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_empty_definition(self):
        """Test when alias has empty definition."""
        alias = Alias(
            name="test",
            definition=None
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/test")

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
            definition=definition.strip()
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/documentation")

        # Should match the primary rule
        self.assertEqual(result, alias)

    def test_get_alias_by_target_path_complex_options(self):
        """Test with complex definition including options."""
        alias = Alias(
            name="blog",
            definition="blog-* -> /posts [glob, ignore-case]"
        )

        db.session.add(alias)
        db.session.commit()

        result = get_alias_by_target_path("/posts")

        # Should not match because it's glob, not literal
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
