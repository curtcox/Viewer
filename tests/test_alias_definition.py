import textwrap
import unittest
from types import SimpleNamespace

from alias_definition import collect_alias_routes, resolve_alias_definition, summarize_definition_lines


class SummarizeDefinitionLinesTests(unittest.TestCase):
    def test_summarize_definition_lines_extracts_metadata(self):
        definition = textwrap.dedent(
            """
            docs -> /docs
            search/* -> /search [glob, ignore-case]
            # comment line
              guide -> /guides
            """
        ).strip("\n")

        summary = summarize_definition_lines(definition, alias_name="docs")

        self.assertEqual(len(summary), 4)

        first = summary[0]
        self.assertTrue(first.is_mapping)
        self.assertEqual(first.match_type, "literal")
        self.assertEqual(first.match_pattern, "/docs")
        self.assertFalse(first.ignore_case)
        self.assertEqual(first.target_path, "/docs")
        self.assertIsNone(first.parse_error)

        second = summary[1]
        self.assertTrue(second.is_mapping)
        self.assertEqual(second.match_type, "glob")
        self.assertEqual(second.match_pattern, "/search/*")
        self.assertTrue(second.ignore_case)
        self.assertEqual(second.target_path, "/search")

        third = summary[2]
        self.assertFalse(third.is_mapping)
        self.assertEqual(third.text.strip(), "# comment line")

        fourth = summary[3]
        self.assertTrue(fourth.is_mapping)
        self.assertEqual(fourth.text, "  guide -> /guides")
        self.assertEqual(fourth.match_pattern, "/docs/guide")
        self.assertEqual(fourth.target_path, "/guides")
        self.assertEqual(fourth.alias_path, "docs/guide")

    def test_collect_alias_routes_includes_nested_entries(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
              api -> /docs/api/architecture/overview.html
              guide -> /guides/getting-started.html
            """
        ).strip("\n")

        alias = SimpleNamespace(
            name="docs",
            match_type="literal",
            match_pattern="/docs",
            target_path="/documentation",
            ignore_case=False,
            definition=definition,
        )

        routes = collect_alias_routes(alias)
        routes_by_path = {route.alias_path: route for route in routes}

        self.assertIn("docs", routes_by_path)
        self.assertIn("docs/api", routes_by_path)
        self.assertIn("docs/guide", routes_by_path)

        self.assertEqual(routes_by_path["docs"].target_path, "/documentation")
        self.assertEqual(
            routes_by_path["docs/api"].target_path,
            "/docs/api/architecture/overview.html",
        )
        self.assertEqual(
            routes_by_path["docs/guide"].target_path,
            "/guides/getting-started.html",
        )

    def test_resolve_alias_definition_returns_shared_metadata(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
              api -> /docs/api/architecture/overview.html
            """
        ).strip("\n")

        alias = SimpleNamespace(
            name="docs",
            match_type="literal",
            match_pattern="/docs",
            target_path="/documentation",
            ignore_case=False,
            definition=definition,
        )

        details = resolve_alias_definition(alias)

        self.assertEqual(len(details.routes), 2)
        self.assertGreaterEqual(len(details.summary), 2)

        alias_paths = {route.alias_path for route in details.routes}
        self.assertIn("docs", alias_paths)
        self.assertIn("docs/api", alias_paths)

        summary_paths = {
            entry.alias_path for entry in details.summary if entry.is_mapping and not entry.parse_error
        }
        self.assertIn("docs/api", summary_paths)

    def test_summarize_definition_lines_reports_parse_errors(self):
        definition = "docs -> /docs [regex, glob]"

        summary = summarize_definition_lines(definition)

        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0].is_mapping)
        self.assertIsNotNone(summary[0].parse_error)
        self.assertIn("only one match type", summary[0].parse_error.lower())


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
