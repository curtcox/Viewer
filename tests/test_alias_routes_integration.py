import unittest
from unittest.mock import Mock

from alias_definition import collect_alias_routes
from models import Alias


class TestAliasRoutesIntegration(unittest.TestCase):
    """Test that collect_alias_routes works with the new Alias model structure."""

    def test_collect_routes_simple_alias(self):
        """Test collecting routes from a simple alias."""
        alias = Alias(
            name="test",
            definition="test -> /target",
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "test")
        self.assertEqual(route.match_type, "literal")
        self.assertEqual(route.match_pattern, "/test")
        self.assertEqual(route.target_path, "/target")
        self.assertFalse(route.ignore_case)
        self.assertIsNone(route.source)

    def test_collect_routes_substitutes_variables_in_target(self):
        """Test that target placeholders pull from resolved variables."""
        alias = Alias(
            name="status",
            definition="status -> {status-page}",
            user_id="user1",
        )

        routes = collect_alias_routes(
            alias, variables={"status-page": "/beageghugragegar"}
        )

        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].target_path, "/beageghugragegar")

    def test_collect_routes_with_multiple_variables(self):
        """Test resolving multiple variables and repeated placeholders."""
        alias = Alias(
            name="reports",
            definition="reports -> /{region}/{section}/{region}",
            user_id="user1",
        )

        variables = {"region": "emea", "section": "status"}

        routes = collect_alias_routes(alias, variables=variables)

        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].target_path, "/emea/status/emea")

    def test_collect_routes_substitutes_variables_in_pattern(self):
        """Test that placeholders in the pattern resolve before parsing."""
        definition = """{prefix} -> /root
  guide -> /guides/{prefix}
        """.strip()
        alias = Alias(
            name="docs",
            definition=definition,
            user_id="user1",
        )

        routes = collect_alias_routes(alias, variables={"prefix": "docs"})

        self.assertGreaterEqual(len(routes), 2)
        nested = next(route for route in routes if route.alias_path == "docs/guide")
        self.assertEqual(nested.match_pattern, "/docs/guide")
        self.assertEqual(nested.target_path, "/guides/docs")

    def test_collect_routes_glob_alias(self):
        """Test collecting routes from a glob alias."""
        alias = Alias(
            name="docs",
            definition="docs/* -> /documentation/?q=* [glob]",
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "docs")
        self.assertEqual(route.match_type, "glob")
        self.assertEqual(route.match_pattern, "/docs/*")
        self.assertEqual(route.target_path, "/documentation/?q=*")
        self.assertFalse(route.ignore_case)

    def test_collect_routes_ignore_case_alias(self):
        """Test collecting routes from an ignore-case alias."""
        alias = Alias(
            name="blog",
            definition="blog-* -> /posts [glob, ignore-case]",
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "blog")
        self.assertEqual(route.match_type, "glob")
        self.assertEqual(route.match_pattern, "/blog-*")
        self.assertEqual(route.target_path, "/posts")
        self.assertTrue(route.ignore_case)

    def test_collect_routes_multi_line_alias(self):
        """Test collecting routes from a multi-line alias."""
        definition = """
        docs -> /documentation
          api -> /docs/api/architecture/overview.html
          guide -> /guides/getting-started.html
        """
        alias = Alias(
            name="docs",
            definition=definition.strip(),
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        # Should have 3 routes: primary + 2 nested
        self.assertEqual(len(routes), 3)

        # Primary route
        primary_route = routes[0]
        self.assertEqual(primary_route.alias_path, "docs")
        self.assertEqual(primary_route.match_type, "literal")
        self.assertEqual(primary_route.match_pattern, "/docs")
        self.assertEqual(primary_route.target_path, "/documentation")

        # Nested routes
        nested_routes = [r for r in routes[1:] if r.source is not None]
        self.assertEqual(len(nested_routes), 2)

        api_route = next(r for r in nested_routes if r.alias_path == "docs/api")
        self.assertEqual(api_route.target_path, "/docs/api/architecture/overview.html")

        guide_route = next(r for r in nested_routes if r.alias_path == "docs/guide")
        self.assertEqual(guide_route.target_path, "/guides/getting-started.html")

    def test_collect_routes_regex_alias(self):
        """Test collecting routes from a regex alias."""
        alias = Alias(
            name="article",
            definition="/article/\\d+ -> /articles [regex]",
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "article")
        self.assertEqual(route.match_type, "regex")
        self.assertEqual(route.match_pattern, "/article/\\d+")
        self.assertEqual(route.target_path, "/articles")
        self.assertFalse(route.ignore_case)

    def test_collect_routes_flask_alias(self):
        """Test collecting routes from a Flask route alias."""
        alias = Alias(
            name="user",
            definition="/user/<id> -> /user-profile/<id>/view [flask]",
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "user")
        self.assertEqual(route.match_type, "flask")
        self.assertEqual(route.match_pattern, "/user/<id>")
        self.assertEqual(route.target_path, "/user-profile/<id>/view")
        self.assertFalse(route.ignore_case)

    def test_collect_routes_fallback_behavior(self):
        """Test that collect_alias_routes handles aliases without helper methods (backwards compatibility)."""
        # Create a mock alias that doesn't have the helper methods
        alias = Mock()
        alias.name = "test"
        alias.definition = "test -> /target"
        alias.user_id = "user1"

        # Remove the helper methods to simulate old-style aliases
        del alias.get_primary_match_type
        del alias.get_primary_match_pattern
        del alias.get_primary_target_path
        del alias.get_primary_ignore_case

        routes = collect_alias_routes(alias)

        # Should still work with fallback behavior
        # The function will process the definition and create routes from it
        self.assertGreaterEqual(len(routes), 1)

        # Find the primary route (first one)
        primary_route = routes[0]
        self.assertEqual(primary_route.alias_path, "test")
        self.assertEqual(primary_route.match_type, "literal")
        self.assertEqual(primary_route.match_pattern, "/test")
        self.assertEqual(primary_route.target_path, "/test")  # Fallback to name-based path
        self.assertFalse(primary_route.ignore_case)

    def test_collect_routes_empty_definition(self):
        """Test collecting routes from an alias with empty definition."""
        alias = Alias(
            name="test",
            definition=None,
            user_id="user1"
        )

        routes = collect_alias_routes(alias)

        # Should have fallback behavior
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.alias_path, "test")
        self.assertEqual(route.match_type, "literal")
        self.assertEqual(route.match_pattern, "/test")
        self.assertEqual(route.target_path, "/test")
        self.assertFalse(route.ignore_case)

    def test_collect_routes_rejects_external_target_fallback(self):
        """Routes are not generated when the definition targets an external URL."""
        alias = Alias(
            name="docs",
            definition="docs -> //external",
            user_id="user1",
        )

        routes = collect_alias_routes(alias)

        self.assertEqual(routes, [])


if __name__ == '__main__':
    unittest.main()
