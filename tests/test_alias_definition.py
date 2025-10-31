import textwrap
import unittest
from types import SimpleNamespace

from alias_definition import (
    AliasDefinitionError,
    collect_alias_routes,
    parse_alias_definition,
    summarize_definition_lines,
)


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

    def test_summarize_definition_lines_flags_text_without_mapping(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
            invalid text
            """
        ).strip("\n")

        summary = summarize_definition_lines(definition, alias_name="docs")

        self.assertEqual(len(summary), 2)
        self.assertTrue(summary[1].is_mapping)
        self.assertIsNotNone(summary[1].parse_error)
        self.assertIn("does not contain an alias mapping", summary[1].parse_error.lower())


class ParseAliasDefinitionValidationTests(unittest.TestCase):
    def test_rejects_definitions_without_mapping_lines(self):
        invalid_definitions = [
            "stuff # invalid",
            "stuff thing # invalid",
            "stuff - thing # invalid",
        ]

        for definition in invalid_definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition)

                message = str(exc_info.exception).lower()
                self.assertIn('pattern -> target', message)

    def test_rejects_invalid_nested_mapping_lines(self):
        invalid_definitions = [
            (
                textwrap.dedent(
                    """
                    docs -> /documentation
                      api ->
                    """
                ).strip("\n"),
                "line 2",
                'target path after "->"',
            ),
            (
                textwrap.dedent(
                    """
                    docs -> /documentation
                      api -> /docs/api [glob, regex]
                    """
                ).strip("\n"),
                "line 2",
                "only one match type",
            ),
            (
                textwrap.dedent(
                    """
                    docs -> /documentation
                      api -> /docs/api [unknown]
                    """
                ).strip("\n"),
                "line 2",
                "unknown alias option",
            ),
        ]

        for definition, expected_line, expected_message in invalid_definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition, alias_name="docs")

                message = str(exc_info.exception).lower()
                self.assertIn(expected_line, message)
                self.assertIn(expected_message, message)

    def test_rejects_definitions_with_non_mapping_lines(self):
        invalid_lines = [
            "stuff # invalid",  # missing mapping arrow
            "stuff thing # invalid",  # missing mapping arrow
            "stuff - thing # invalid",  # missing mapping arrow
        ]

        for invalid_line in invalid_lines:
            definition = textwrap.dedent(
                f"""
                docs -> /documentation
                {invalid_line}
                """
            ).strip("\n")

            with self.subTest(invalid_line=invalid_line):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition, alias_name="docs")

                message = str(exc_info.exception).lower()
                self.assertIn("line 2", message)
                self.assertIn("does not contain an alias mapping", message)

    def test_rejects_invalid_target_paths(self):
        invalid_definitions = [
            "stuff -> }",
            "stuff -> {",
            "stuff -> {}",
            "stuff -> {thing}",
        ]

        for definition in invalid_definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition)

                message = str(exc_info.exception).lower()
                self.assertIn("valid alias or url", message)

    def test_rejects_invalid_nested_target_paths(self):
        invalid_targets = ["}", "{", "{}", "{thing}"]

        for target in invalid_targets:
            definition = textwrap.dedent(
                f"""
                docs -> /documentation
                  nested -> {target}
                """
            ).strip("\n")

            with self.subTest(target=target):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition, alias_name="docs")

                message = str(exc_info.exception).lower()
                self.assertIn("line 2", message)
                self.assertIn("valid alias or url", message)


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
