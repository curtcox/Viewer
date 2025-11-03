import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from alias_definition import (
    AliasDefinitionError,
    collect_alias_routes,
    definition_contains_mapping,
    ensure_primary_line,
    format_primary_alias_line,
    get_primary_alias_route,
    parse_alias_definition,
    replace_primary_definition_line,
    summarize_definition_lines,
)


class FormatPrimaryAliasLineTests(unittest.TestCase):
    def test_format_primary_alias_line_with_literal_match(self):
        result = format_primary_alias_line("literal", "/docs", "/documentation")
        self.assertEqual(result, "docs -> /documentation")

    def test_format_primary_alias_line_with_glob_match(self):
        result = format_primary_alias_line("glob", "/docs/*", "/documentation")
        self.assertEqual(result, "/docs/* -> /documentation [glob]")

    def test_format_primary_alias_line_with_ignore_case(self):
        result = format_primary_alias_line("literal", "/docs", "/documentation", ignore_case=True)
        self.assertEqual(result, "docs -> /documentation [ignore-case]")

    def test_format_primary_alias_line_with_alias_name(self):
        result = format_primary_alias_line("literal", None, "/documentation", alias_name="docs")
        self.assertEqual(result, "docs -> /documentation")

    def test_format_primary_alias_line_with_regex_and_ignore_case(self):
        result = format_primary_alias_line("regex", r"/article/\d+", "/articles", ignore_case=True)
        self.assertEqual(result, r"/article/\d+ -> /articles [regex, ignore-case]")


class EdgeCaseTests(unittest.TestCase):
    def test_parse_alias_definition_with_none_definition(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition(None)
        self.assertIn("pattern -> target", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_empty_target(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs ->")
        self.assertIn("target path", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_whitespace_target(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs ->   ")
        self.assertIn("target path", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_unclosed_options(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob")
        self.assertIn("closed with", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_text_after_closing_bracket(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob] extra")
        self.assertIn("unexpected text", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_conflicting_match_types(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob, regex]")
        self.assertIn("only one match type", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_unknown_option(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [invalid-option]")
        self.assertIn("unknown alias option", str(exc_info.exception).lower())

    def test_replace_primary_definition_line_with_empty_primary_line(self):
        result = replace_primary_definition_line("docs -> /old", "")
        self.assertEqual(result, "docs -> /old")

    def test_replace_primary_definition_line_with_none_definition(self):
        result = replace_primary_definition_line(None, "docs -> /new")
        self.assertEqual(result, "docs -> /new")

    def test_replace_primary_definition_line_with_empty_definition(self):
        result = replace_primary_definition_line("   ", "docs -> /new")
        self.assertEqual(result, "docs -> /new")

    def test_ensure_primary_line_with_empty_cleaned_text(self):
        # This tests line 347-348: after stripping, if empty, return primary_line
        result = ensure_primary_line("   \n   ", "docs -> /documentation")
        self.assertEqual(result, "docs -> /documentation")

    def test_summarize_definition_lines_with_empty_lines(self):
        definition = textwrap.dedent(
            '''
            docs -> /documentation

            
            api -> /docs/api
            '''
        ).strip("\n")

        summary = summarize_definition_lines(definition, alias_name="docs")
        # Check that empty lines are properly summarized
        self.assertTrue(any(not line.is_mapping and not line.text.strip() for line in summary))

    def test_summarize_definition_lines_with_tabs(selfn):
        definition = "docs -> /documentation\n\tapi -> /docs/api"
        summary = summarize_definition_lines(definition, alias_name="docs")
        self.assertEqual(len(summary), 2)
        # Tab should be expanded to 2 spaces per pytest.ini tab width
        self.assertEqual(summary[1].depth, 1)

    def test_collect_alias_routes_with_empty_definition(self):
        alias = SimpleNamespace(name="docs", definition="")
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "docs")
        self.assertEqual(routes[0].match_pattern, "/docs")

    def test_collect_alias_routes_with_external_target(self):
        alias = SimpleNamespace(name="docs", definition="docs -> https://example.com")
        routes = collect_alias_routes(alias)
        # External targets should result in empty routes
        self.assertEqual(len(routes), 0)

    def test_collect_alias_routes_with_mock_alias(self):
        # Test the Mock detection path (lines 593-599)
        alias = Mock()
        alias.name = "test"
        alias.definition = "test -> /target"
        routes = collect_alias_routes(alias)
        # Mock aliases should get a self-route
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "test")

    def test_get_primary_alias_route(self):
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /documentation"
        )
        route = get_primary_alias_route(alias)
        self.assertIsNotNone(route)
        self.assertEqual(route.alias_path, "docs")
        self.assertEqual(route.target_path, "/documentation")

    def test_get_primary_alias_route_with_no_routes(self):
        alias = SimpleNamespace(name="docs", definition="docs -> https://example.com")
        route = get_primary_alias_route(alias)
        self.assertIsNone(route)


class VariableSubstitutionTests(unittest.TestCase):
    def test_collect_alias_routes_with_variable_substitution(self):
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /user/{user_id}/docs",
            user_id=None,
            _resolved_variables={"user_id": "123"}
        )
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].target_path, "/user/123/docs")

    def test_collect_alias_routes_with_provided_variables(self):
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /user/{user_id}/docs"
        )
        routes = collect_alias_routes(alias, variables={"user_id": "456"})
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].target_path, "/user/456/docs")

    def test_collect_alias_routes_with_no_variable_match(self):
        # Test line 212-214: variable name not in variables dict
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /user/{unknown}/docs",
            _resolved_variables={"user_id": "123"}
        )
        routes = collect_alias_routes(alias)
        # Unknown variable should remain unreplaced
        self.assertEqual(routes[0].target_path, "/user/{unknown}/docs")

    def test_collect_alias_routes_with_empty_variable_name(self):
        # Test line 212: empty variable name
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /user/{}/docs",
            _resolved_variables={"": "value"}
        )
        routes = collect_alias_routes(alias)
        # Empty variable name should remain unreplaced
        self.assertEqual(routes[0].target_path, "/user/{}/docs")

    def test_collect_alias_routes_with_iterable_variables(self):
        # Test _normalize_variable_map with non-Mapping iterable (lines 140-151)
        var1 = SimpleNamespace(name="var1", definition="value1", enabled=True)
        var2 = SimpleNamespace(name="var2", definition="value2", enabled=False)  # disabled
        var3 = SimpleNamespace(name="var3", definition="value3")  # no enabled attr
        var4 = SimpleNamespace(name=None, definition="value4")  # None name
        var5 = SimpleNamespace(name="", definition="value5")  # empty name
        var6 = SimpleNamespace(name="var6", definition=None)  # None definition
        var7 = None  # None entry
        
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /{var1}/{var3}/path",
            resolved_variables=[var1, var2, var3, var4, var5, var6, var7]
        )
        routes = collect_alias_routes(alias)
        # Should substitute var1 and var3, skip var2 (disabled), var4 (None name), var5 (empty name), var6 (None def), var7 (None)
        self.assertEqual(routes[0].target_path, "/value1/value3/path")

    def test_collect_alias_routes_with_non_iterable_variables(self):
        # Test _normalize_variable_map with non-iterable (line 138-139)
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /path",
            resolved_variables=42  # not iterable
        )
        routes = collect_alias_routes(alias)
        # Should handle gracefully
        self.assertEqual(len(routes), 1)

    def test_collect_alias_routes_with_none_variable_key(self):
        # Test line 156-157: None key in mapping
        alias = SimpleNamespace(
            name="docs",
            definition="docs -> /path",
            _resolved_variables={None: "value", "": "empty", "key": "valid"}
        )
        routes = collect_alias_routes(alias)
        # Should skip None and empty keys
        self.assertEqual(len(routes), 1)


class TargetPathValidationTests(unittest.TestCase):
    def test_parse_alias_definition_with_symbol_only_target(self):
        # Test line 100-101: no alphanumeric characters
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> ///")
        self.assertIn("valid alias or url", str(exc_info.exception).lower())

    def test_parse_alias_definition_with_double_slash_target(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> //external-site")
        self.assertIn("stay within this application", str(exc_info.exception).lower())


class InlineCommentTests(unittest.TestCase):
    def test_parse_alias_definition_with_inline_comment_after_target(self):
        # Inline comments after the target should be stripped
        parsed = parse_alias_definition("docs -> /documentation # inline comment")
        self.assertEqual(parsed.target_path, "/documentation")

    def test_parse_alias_definition_with_inline_comment_after_options(self):
        # Test the _strip_inline_comment with different positions (line 78)
        parsed = parse_alias_definition("docs -> /documentation [glob] # comment")
        self.assertEqual(parsed.target_path, "/documentation")
        self.assertEqual(parsed.match_type, "glob")


class DefinitionSummaryDepthTests(unittest.TestCase):
    def test_summarize_definition_lines_with_deep_nesting(self):
        definition = textwrap.dedent(
            '''
            root -> /root
              level1 -> /level1
                level2 -> /level2
                  level3 -> /level3
            '''
        ).strip("\n")
        summary = summarize_definition_lines(definition, alias_name="root")
        depths = [line.depth for line in summary if line.is_mapping]
        self.assertEqual(depths, [0, 1, 2, 3])

    def test_summarize_definition_lines_with_non_literal_nested(self):
        definition = textwrap.dedent(
            '''
            root -> /root
              /glob/* -> /target [glob]
            '''
        ).strip("\n")
        summary = summarize_definition_lines(definition, alias_name="root")
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[1].match_type, "glob")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()