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
    _extract_primary_line,
    _normalize_variable_map,
    _strip_inline_comment,
    _substitute_variables,
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
            "xy -> {xdd",
        ]

        for definition in invalid_definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition)

                message = str(exc_info.exception).lower()
                self.assertIn("valid alias or url", message)

    def test_rejects_invalid_nested_target_paths(self):
        invalid_targets = ["}", "{", "{}", "{thing}", "{xdd"]

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

    def test_rejects_targets_outside_application(self):
        definitions = [
            "docs -> //external",
            "docs -> https://example.com",
        ]

        for definition in definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(AliasDefinitionError) as exc_info:
                    parse_alias_definition(definition)

                message = str(exc_info.exception)
                self.assertIn("stay within this application", message)

    def test_accepts_ignore_case_and_match_type_options(self):
        parsed = parse_alias_definition("docs/* -> /documentation [glob, ignorecase]")

        self.assertEqual(parsed.match_type, "glob")
        self.assertTrue(parsed.ignore_case)
        self.assertEqual(parsed.target_path, "/documentation")


class DefinitionUtilityTests(unittest.TestCase):
    def test_definition_contains_mapping_detects_primary_line(self):
        self.assertFalse(definition_contains_mapping(None))
        self.assertFalse(definition_contains_mapping("  # comment"))
        self.assertTrue(definition_contains_mapping("docs -> /documentation"))

    def test_ensure_primary_line_inserts_when_missing(self):
        updated = ensure_primary_line("  notes", "docs -> /documentation")

        self.assertEqual(updated, "docs -> /documentation\n\nnotes")

    def test_ensure_primary_line_preserves_existing_mapping(self):
        definition = "docs -> /documentation\nnotes"

        self.assertEqual(
            ensure_primary_line(definition, "docs -> /other"),
            definition,
        )

    def test_replace_primary_definition_line_preserves_indentation(self):
        definition = textwrap.dedent(
            """
                docs -> /old
                  nested -> /nested
            """
        ).strip("\n")

        updated = replace_primary_definition_line(definition, "docs -> /new")

        self.assertEqual(
            updated,
            textwrap.dedent(
                """
                    docs -> /new
                      nested -> /nested
                """
            ).strip("\n"),
        )

    def test_replace_primary_definition_line_appends_when_missing(self):
        definition = "Notes about the alias"

        updated = replace_primary_definition_line(definition, "docs -> /documentation")

        self.assertEqual(updated, "docs -> /documentation\n\nNotes about the alias")


class StripInlineCommentTests(unittest.TestCase):
    def test_strips_inline_comment(self):
        self.assertEqual(_strip_inline_comment("docs -> /docs # comment"), "docs -> /docs")
        self.assertEqual(_strip_inline_comment("docs -> /docs  # comment"), "docs -> /docs")
        self.assertEqual(_strip_inline_comment("docs -> /docs\t# comment"), "docs -> /docs")

    def test_preserves_line_without_comment(self):
        self.assertEqual(_strip_inline_comment("docs -> /docs"), "docs -> /docs")
        self.assertEqual(_strip_inline_comment("docs"), "docs")

    def test_handles_empty_string(self):
        self.assertEqual(_strip_inline_comment(""), "")

    def test_preserves_comment_only_line_without_leading_space(self):
        # The function only strips comments with preceding whitespace (inline comments)
        self.assertEqual(_strip_inline_comment("# comment"), "# comment")

    def test_strips_comment_with_leading_space(self):
        self.assertEqual(_strip_inline_comment("  # comment"), "")


class ExtractPrimaryLineTests(unittest.TestCase):
    def test_extracts_first_mapping_line(self):
        definition = "# comment\ndocs -> /documentation\nother -> /other"
        self.assertEqual(_extract_primary_line(definition), "docs -> /documentation")

    def test_skips_blank_lines(self):
        definition = "\n\n  \ndocs -> /documentation"
        self.assertEqual(_extract_primary_line(definition), "docs -> /documentation")

    def test_skips_comment_lines(self):
        definition = "# comment 1\n# comment 2\ndocs -> /documentation"
        self.assertEqual(_extract_primary_line(definition), "docs -> /documentation")

    def test_returns_none_for_no_mapping(self):
        self.assertIsNone(_extract_primary_line("# comment only"))
        self.assertIsNone(_extract_primary_line("no mapping here"))
        self.assertIsNone(_extract_primary_line(""))

    def test_preserves_inline_comment(self):
        definition = "docs -> /documentation # inline comment"
        self.assertEqual(_extract_primary_line(definition), "docs -> /documentation # inline comment")


class NormalizeVariableMapTests(unittest.TestCase):
    def test_handles_none_and_empty(self):
        self.assertEqual(_normalize_variable_map(None), {})
        self.assertEqual(_normalize_variable_map({}), {})
        self.assertEqual(_normalize_variable_map([]), {})

    def test_handles_dictionary_input(self):
        variables = {"var1": "value1", "var2": "value2"}
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1", "var2": "value2"})

    def test_handles_object_list_with_name_and_definition(self):
        variables = [
            SimpleNamespace(name="var1", definition="value1"),
            SimpleNamespace(name="var2", definition="value2"),
        ]
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1", "var2": "value2"})

    def test_skips_disabled_variables(self):
        variables = [
            SimpleNamespace(name="var1", definition="value1", enabled=True),
            SimpleNamespace(name="var2", definition="value2", enabled=False),
            SimpleNamespace(name="var3", definition="value3", enabled=True),
        ]
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1", "var3": "value3"})

    def test_skips_none_entries(self):
        variables = [
            SimpleNamespace(name="var1", definition="value1"),
            None,
            SimpleNamespace(name="var2", definition="value2"),
        ]
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1", "var2": "value2"})

    def test_skips_entries_without_name(self):
        variables = [
            SimpleNamespace(name="var1", definition="value1"),
            SimpleNamespace(definition="value2"),
            SimpleNamespace(name="", definition="value3"),
        ]
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1"})

    def test_skips_entries_without_definition(self):
        variables = [
            SimpleNamespace(name="var1", definition="value1"),
            SimpleNamespace(name="var2"),
        ]
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"var1": "value1"})

    def test_converts_values_to_strings(self):
        variables = {"num": 123, "bool": True, "none": None}
        result = _normalize_variable_map(variables)
        self.assertEqual(result, {"num": "123", "bool": "True", "none": ""})

    def test_handles_non_iterable_input(self):
        result = _normalize_variable_map(123)
        self.assertEqual(result, {})


class SubstituteVariablesTests(unittest.TestCase):
    def test_substitutes_single_variable(self):
        text = "Path: {var1}"
        variables = {"var1": "value1"}
        self.assertEqual(_substitute_variables(text, variables), "Path: value1")

    def test_substitutes_multiple_variables(self):
        text = "{var1}/{var2}/{var3}"
        variables = {"var1": "a", "var2": "b", "var3": "c"}
        self.assertEqual(_substitute_variables(text, variables), "a/b/c")

    def test_preserves_unknown_variables(self):
        text = "{var1}/{unknown}/{var2}"
        variables = {"var1": "a", "var2": "b"}
        self.assertEqual(_substitute_variables(text, variables), "a/{unknown}/b")

    def test_handles_empty_variable_name(self):
        text = "{}/{var1}"
        variables = {"var1": "value"}
        self.assertEqual(_substitute_variables(text, variables), "{}/value")

    def test_handles_none_text(self):
        self.assertIsNone(_substitute_variables(None, {"var": "value"}))

    def test_handles_empty_text(self):
        self.assertEqual(_substitute_variables("", {"var": "value"}), "")

    def test_handles_empty_variables(self):
        self.assertEqual(_substitute_variables("{var}", {}), "{var}")

    def test_handles_variables_with_special_chars_in_name(self):
        text = "{var-1}/{var.2}/{var_3}"
        variables = {"var-1": "a", "var.2": "b", "var_3": "c"}
        self.assertEqual(_substitute_variables(text, variables), "a/b/c")


class FormatPrimaryAliasLineTests(unittest.TestCase):
    def test_formats_literal_match_without_options(self):
        result = format_primary_alias_line("literal", "/docs", "/documentation", alias_name="docs")
        self.assertEqual(result, "docs -> /documentation")

    def test_formats_literal_match_with_pattern(self):
        result = format_primary_alias_line("literal", "/docs", "/documentation")
        self.assertEqual(result, "docs -> /documentation")

    def test_formats_glob_match(self):
        result = format_primary_alias_line("glob", "/docs/*", "/documentation")
        self.assertEqual(result, "/docs/* -> /documentation [glob]")

    def test_formats_regex_match(self):
        result = format_primary_alias_line("regex", r"/docs/\d+", "/documentation")
        self.assertEqual(result, r"/docs/\d+ -> /documentation [regex]")

    def test_formats_flask_match(self):
        result = format_primary_alias_line("flask", "/docs/<id>", "/documentation/<id>")
        self.assertEqual(result, "/docs/<id> -> /documentation/<id> [flask]")

    def test_includes_ignore_case_option(self):
        result = format_primary_alias_line("literal", "/docs", "/documentation", ignore_case=True, alias_name="docs")
        self.assertEqual(result, "docs -> /documentation [ignore-case]")

    def test_includes_both_match_type_and_ignore_case(self):
        result = format_primary_alias_line("glob", "/docs/*", "/documentation", ignore_case=True)
        self.assertEqual(result, "/docs/* -> /documentation [glob, ignore-case]")

    def test_handles_empty_pattern_with_alias_name(self):
        result = format_primary_alias_line("literal", None, "/documentation", alias_name="docs")
        self.assertEqual(result, "docs -> /documentation")

    def test_handles_empty_pattern_without_alias_name(self):
        result = format_primary_alias_line("literal", None, "/documentation")
        self.assertEqual(result, "/ -> /documentation")

    def test_normalizes_match_type(self):
        result = format_primary_alias_line("GLOB", "/docs/*", "/documentation")
        self.assertEqual(result, "/docs/* -> /documentation [glob]")


class GetPrimaryAliasRouteTests(unittest.TestCase):
    def test_returns_first_route(self):
        definition = "docs -> /documentation\napi -> /api"
        alias = SimpleNamespace(name="docs", definition=definition)
        route = get_primary_alias_route(alias)
        self.assertIsNotNone(route)
        self.assertEqual(route.alias_path, "docs")
        self.assertEqual(route.target_path, "/documentation")

    def test_returns_none_for_no_routes(self):
        alias = SimpleNamespace(name="", definition="")
        route = get_primary_alias_route(alias)
        self.assertIsNone(route)


class CollectAliasRoutesEdgeCasesTests(unittest.TestCase):
    def test_handles_empty_definition(self):
        alias = SimpleNamespace(name="docs", definition="")
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "docs")
        self.assertEqual(routes[0].match_pattern, "/docs")
        self.assertEqual(routes[0].target_path, "/docs")

    def test_handles_none_definition(self):
        alias = SimpleNamespace(name="docs", definition=None)
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "docs")

    def test_handles_mock_object(self):
        alias = Mock()
        alias.name = "docs"
        alias.definition = None
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "docs")
        self.assertEqual(routes[0].match_pattern, "/docs")

    def test_substitutes_variables_in_definition(self):
        definition = "docs/{var1} -> /documentation/{var2}"
        variables = {"var1": "api", "var2": "reference"}
        alias = SimpleNamespace(name="docs", definition=definition)
        routes = collect_alias_routes(alias, variables=variables)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].match_pattern, "/docs/api")
        self.assertEqual(routes[0].target_path, "/documentation/reference")

    def test_deduplicates_routes(self):
        definition = textwrap.dedent(
            """
            docs -> /documentation
            docs -> /documentation
            api -> /api
            """
        ).strip()
        alias = SimpleNamespace(name="docs", definition=definition)
        routes = collect_alias_routes(alias)
        # Should only have 2 unique routes, not 3
        self.assertEqual(len(routes), 2)

    def test_handles_external_target_error(self):
        definition = "docs -> https://example.com"
        alias = SimpleNamespace(name="docs", definition=definition)
        routes = collect_alias_routes(alias)
        # Should return empty list for external targets
        self.assertEqual(len(routes), 0)

    def test_handles_parse_error_fallback(self):
        definition = "docs -> /docs [invalid-option]"
        alias = SimpleNamespace(name="docs", definition=definition)
        routes = collect_alias_routes(alias)
        # Should fall back to name-based route
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].alias_path, "docs")

    def test_resolves_variables_from_alias_attributes(self):
        definition = "docs -> /documentation/{var1}"
        alias = SimpleNamespace(
            name="docs",
            definition=definition,
            resolved_variables={"var1": "value1"}
        )
        routes = collect_alias_routes(alias)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].target_path, "/documentation/value1")


class ParseAliasDefinitionEdgeCasesTests(unittest.TestCase):
    def test_handles_none_definition(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition(None)
        self.assertIn("pattern -> target", str(exc_info.exception).lower())

    def test_handles_empty_definition(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("")
        self.assertIn("pattern -> target", str(exc_info.exception).lower())

    def test_rejects_missing_target_after_arrow(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs ->")
        self.assertIn('target path after "->"', str(exc_info.exception).lower())

    def test_rejects_arrow_in_comment_only(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs # -> /docs")
        self.assertIn("pattern -> target", str(exc_info.exception).lower())

    def test_rejects_unclosed_options_bracket(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob")
        self.assertIn('closed with "]"', str(exc_info.exception).lower())

    def test_rejects_mismatched_options_brackets(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation ]glob[")
        self.assertIn('closed with "]"', str(exc_info.exception).lower())

    def test_rejects_text_after_options_bracket(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob] extra")
        self.assertIn("unexpected text after", str(exc_info.exception).lower())

    def test_accepts_empty_options(self):
        parsed = parse_alias_definition("docs -> /documentation []")
        self.assertEqual(parsed.match_type, "literal")
        self.assertEqual(parsed.target_path, "/documentation")

    def test_accepts_whitespace_in_options(self):
        parsed = parse_alias_definition("docs -> /documentation [ glob , ignore-case ]")
        self.assertEqual(parsed.match_type, "glob")
        self.assertTrue(parsed.ignore_case)

    def test_handles_multiple_arrows(self):
        # Only the first -> should be used for splitting
        parsed = parse_alias_definition("docs -> /path->with->arrows")
        self.assertEqual(parsed.target_path, "/path->with->arrows")

    def test_preserves_pattern_text(self):
        parsed = parse_alias_definition("custom-pattern -> /documentation", alias_name="docs")
        self.assertEqual(parsed.pattern_text, "custom-pattern")

    def test_uses_alias_name_for_empty_pattern(self):
        parsed = parse_alias_definition(" -> /documentation", alias_name="docs")
        self.assertEqual(parsed.pattern_text, "docs")

    def test_rejects_target_with_only_special_chars(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> ///")
        self.assertIn("valid alias or url", str(exc_info.exception).lower())

    def test_accepts_target_with_query_params(self):
        parsed = parse_alias_definition("docs -> /documentation?q=test")
        self.assertEqual(parsed.target_path, "/documentation?q=test")

    def test_accepts_target_with_fragment(self):
        parsed = parse_alias_definition("docs -> /documentation#section")
        self.assertEqual(parsed.target_path, "/documentation#section")

    def test_rejects_duplicate_match_types(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [glob, regex]")
        self.assertIn("only one match type", str(exc_info.exception).lower())

    def test_rejects_unknown_option(self):
        with self.assertRaises(AliasDefinitionError) as exc_info:
            parse_alias_definition("docs -> /documentation [unknown-option]")
        self.assertIn("unknown alias option", str(exc_info.exception).lower())

    def test_accepts_ignore_case_variations(self):
        # Test "ignore-case"
        parsed1 = parse_alias_definition("docs -> /documentation [ignore-case]")
        self.assertTrue(parsed1.ignore_case)

        # Test "ignorecase"
        parsed2 = parse_alias_definition("docs -> /documentation [ignorecase]")
        self.assertTrue(parsed2.ignore_case)


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
