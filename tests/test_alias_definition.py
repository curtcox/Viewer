import textwrap
import unittest
from types import SimpleNamespace

from alias_definition import collect_alias_routes, summarize_definition_lines


class SummarizeDefinitionLinesTests(unittest.TestCase):
    def test_summarize_definition_lines_extracts_metadata(self):
        definition = textwrap.dedent(
            """
            docs/* -> /documentation/?q=* [glob]
            docs -> /documentation
              api -> /docs/api/architecture/overview.html
              guide -> /guides/getting-started.html
            # comment line
            blog-* -> /posts [glob, ignore-case]
            /article/\\d+ -> /articles [regex]
            /user/<id> -> /user-profile/<id>/view [flask]
            """
        ).strip("\n")

        summary = summarize_definition_lines(definition, alias_name="docs")

        self.assertEqual(len(summary), 8)

        first = summary[0]
        self.assertTrue(first.is_mapping)
        self.assertEqual(first.match_type, "glob")
        self.assertEqual(first.match_pattern, "/docs/*")
        self.assertFalse(first.ignore_case)
        self.assertEqual(first.target_path, "/documentation/?q=*")
        self.assertIsNone(first.parse_error)

        second = summary[1]
        self.assertTrue(second.is_mapping)
        self.assertEqual(second.match_type, "literal")
        self.assertEqual(second.match_pattern, "/docs")
        self.assertFalse(second.ignore_case)
        self.assertEqual(second.target_path, "/documentation")
        self.assertEqual(second.alias_path, "docs")

        third = summary[2]
        self.assertTrue(third.is_mapping)
        self.assertEqual(third.text, "  api -> /docs/api/architecture/overview.html")
        self.assertEqual(third.match_pattern, "/docs/api")
        self.assertEqual(third.target_path, "/docs/api/architecture/overview.html")
        self.assertEqual(third.alias_path, "docs/api")

        fourth = summary[3]
        self.assertTrue(fourth.is_mapping)
        self.assertEqual(fourth.text, "  guide -> /guides/getting-started.html")
        self.assertEqual(fourth.match_pattern, "/docs/guide")
        self.assertEqual(fourth.target_path, "/guides/getting-started.html")
        self.assertEqual(fourth.alias_path, "docs/guide")

        fifth = summary[4]
        self.assertFalse(fifth.is_mapping)
        self.assertEqual(fifth.text.strip(), "# comment line")

        sixth = summary[5]
        self.assertTrue(sixth.is_mapping)
        self.assertEqual(sixth.match_type, "glob")
        self.assertTrue(sixth.ignore_case)
        self.assertEqual(sixth.match_pattern, "/blog-*")
        self.assertEqual(sixth.target_path, "/posts")

        seventh = summary[6]
        self.assertTrue(seventh.is_mapping)
        self.assertEqual(seventh.match_type, "regex")
        self.assertEqual(seventh.match_pattern, r"/article/\d+")
        self.assertEqual(seventh.target_path, "/articles")

        eighth = summary[7]
        self.assertTrue(eighth.is_mapping)
        self.assertEqual(eighth.match_type, "flask")
        self.assertEqual(eighth.match_pattern, "/user/<id>")
        self.assertEqual(eighth.target_path, "/user-profile/<id>/view")

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

    def test_summarize_definition_lines_reports_parse_errors(self):
        definition = "docs -> /docs [regex, glob]"

        summary = summarize_definition_lines(definition)

        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0].is_mapping)
        self.assertIsNotNone(summary[0].parse_error)
        self.assertIn("only one match type", summary[0].parse_error.lower())


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
