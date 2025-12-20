import unittest

from models import Alias


class TestAliasModel(unittest.TestCase):
    """Test the Alias model helper methods."""

    def test_get_primary_target_path_simple_definition(self):
        """Test getting target path from a simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertEqual(alias.get_primary_target_path(), "/target")

    def test_get_primary_target_path_with_variable_reference(self):
        """Test that variable placeholders resolve before accessing the target path."""
        alias = Alias(
            name="status",
            definition="status -> {status-page}",
        )
        alias._resolved_variables = {"status-page": "/beageghugragegar"}

        self.assertEqual(alias.get_primary_target_path(), "/beageghugragegar")

    def test_get_primary_target_path_fallback(self):
        """Test fallback when definition parsing fails."""
        alias = Alias(
            name="test",
            definition="invalid definition",
        )
        self.assertEqual(alias.get_primary_target_path(), "/test")

    def test_get_primary_target_path_empty_name_fallback(self):
        """Test fallback when name is empty."""
        alias = Alias(
            name="",
            definition="invalid definition",
        )
        self.assertEqual(alias.get_primary_target_path(), "/")

    def test_get_primary_match_type_simple_definition(self):
        """Test getting match type from a simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertEqual(alias.get_primary_match_type(), "literal")

    def test_get_primary_match_type_glob(self):
        """Test getting glob match type."""
        alias = Alias(
            name="test",
            definition="test* -> /target [glob]",
        )
        self.assertEqual(alias.get_primary_match_type(), "glob")

    def test_get_primary_match_type_fallback(self):
        """Test fallback when definition parsing fails."""
        alias = Alias(
            name="test",
            definition="invalid definition",
        )
        self.assertEqual(alias.get_primary_match_type(), "literal")

    def test_get_primary_match_pattern_simple_definition(self):
        """Test getting match pattern from a simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertEqual(alias.get_primary_match_pattern(), "/test")

    def test_get_primary_match_pattern_glob(self):
        """Test getting glob match pattern."""
        alias = Alias(
            name="test",
            definition="test* -> /target [glob]",
        )
        self.assertEqual(alias.get_primary_match_pattern(), "/test*")

    def test_get_primary_match_pattern_fallback(self):
        """Test fallback when definition parsing fails."""
        alias = Alias(
            name="test",
            definition="invalid definition",
        )
        self.assertEqual(alias.get_primary_match_pattern(), "/test")

    def test_get_primary_ignore_case_simple_definition(self):
        """Test getting ignore_case from a simple definition."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertFalse(alias.get_primary_ignore_case())

    def test_get_primary_ignore_case_enabled(self):
        """Test getting ignore_case when enabled."""
        alias = Alias(
            name="test",
            definition="test -> /target [ignore-case]",
        )
        self.assertTrue(alias.get_primary_ignore_case())

    def test_get_primary_ignore_case_fallback(self):
        """Test fallback when definition parsing fails."""
        alias = Alias(
            name="test",
            definition="invalid definition",
        )
        self.assertFalse(alias.get_primary_ignore_case())

    def test_get_effective_pattern(self):
        """Test the get_effective_pattern method for backwards compatibility."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertEqual(alias.get_effective_pattern(), "/test")

    def test_repr_with_helper_methods(self):
        """Test that __repr__ uses the helper methods."""
        alias = Alias(
            name="test",
            definition="test -> /target",
        )
        self.assertEqual(repr(alias), "<Alias test -> /target>")

    def test_multi_line_definition_primary_extraction(self):
        """Test that helper methods work with multi-line definitions by extracting the primary rule."""
        definition = """
        docs -> /documentation
          api -> /docs/api/architecture/overview.html
          guide -> /guides/getting-started.html
        """
        alias = Alias(
            name="docs",
            definition=definition.strip(),
        )

        # Should extract the primary rule (first line)
        self.assertEqual(alias.get_primary_target_path(), "/documentation")
        self.assertEqual(alias.get_primary_match_type(), "literal")
        self.assertEqual(alias.get_primary_match_pattern(), "/docs")
        self.assertFalse(alias.get_primary_ignore_case())

    def test_complex_definition_with_options(self):
        """Test helper methods with complex definitions including options."""
        definition = "blog-* -> /posts [glob, ignore-case]"
        alias = Alias(
            name="blog",
            definition=definition,
        )

        self.assertEqual(alias.get_primary_target_path(), "/posts")
        self.assertEqual(alias.get_primary_match_type(), "glob")
        self.assertEqual(alias.get_primary_match_pattern(), "/blog-*")
        self.assertTrue(alias.get_primary_ignore_case())

    def test_regex_definition(self):
        """Test helper methods with regex definitions."""
        definition = "/article/\\d+ -> /articles [regex]"
        alias = Alias(
            name="article",
            definition=definition,
        )

        self.assertEqual(alias.get_primary_target_path(), "/articles")
        self.assertEqual(alias.get_primary_match_type(), "regex")
        self.assertEqual(alias.get_primary_match_pattern(), "/article/\\d+")
        self.assertFalse(alias.get_primary_ignore_case())

    def test_flask_definition(self):
        """Test helper methods with Flask route definitions."""
        definition = "/user/<id> -> /user-profile/<id>/view [flask]"
        alias = Alias(
            name="user",
            definition=definition,
        )

        self.assertEqual(alias.get_primary_target_path(), "/user-profile/<id>/view")
        self.assertEqual(alias.get_primary_match_type(), "flask")
        self.assertEqual(alias.get_primary_match_pattern(), "/user/<id>")
        self.assertFalse(alias.get_primary_ignore_case())


if __name__ == "__main__":
    unittest.main()
