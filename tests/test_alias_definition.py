import textwrap
import unittest

from alias_definition import summarize_definition_lines


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
        self.assertEqual(fourth.match_pattern, "/guide")
        self.assertEqual(fourth.target_path, "/guides")

    def test_summarize_definition_lines_reports_parse_errors(self):
        definition = "docs -> /docs [regex, glob]"

        summary = summarize_definition_lines(definition)

        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0].is_mapping)
        self.assertIsNotNone(summary[0].parse_error)
        self.assertIn("only one match type", summary[0].parse_error.lower())


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
