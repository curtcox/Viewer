"""Unit tests for server_execution/pipeline_execution.py."""

import unittest
from unittest.mock import MagicMock, patch

from server_execution.pipeline_execution import (
    DataExtensionError,
    ParameterInfo,
    PathSegmentInfo,
    PipelineExecutionResult,
    UnrecognizedExtensionError,
    analyze_segment,
    check_chaining_support,
    detect_language_from_suffix,
    get_resolution_type,
    get_server_info,
    resolve_aliases,
    resolve_segment_type,
    validate_cid,
)


class TestDetectLanguageFromSuffix(unittest.TestCase):
    """Test detect_language_from_suffix function."""

    def test_sh_is_bash(self):
        """Bash suffix returns bash."""
        self.assertEqual(detect_language_from_suffix("script.sh"), "bash")

    def test_py_is_python(self):
        """Python suffix returns python."""
        self.assertEqual(detect_language_from_suffix("script.py"), "python")

    def test_js_is_javascript(self):
        """JavaScript suffix returns javascript."""
        self.assertEqual(detect_language_from_suffix("script.js"), "javascript")

    def test_ts_is_typescript(self):
        """TypeScript suffix returns typescript."""
        self.assertEqual(detect_language_from_suffix("script.ts"), "typescript")

    def test_clj_is_clojure(self):
        """Clojure suffix returns clojure."""
        self.assertEqual(detect_language_from_suffix("script.clj"), "clojure")

    def test_cljs_is_clojurescript(self):
        """ClojureScript suffix returns clojurescript."""
        self.assertEqual(detect_language_from_suffix("script.cljs"), "clojurescript")

    def test_unknown_suffix_raises_error(self):
        """Unrecognized suffix should raise error."""
        with self.assertRaises(UnrecognizedExtensionError) as ctx:
            detect_language_from_suffix("data.xyz")
        self.assertEqual(ctx.exception.extension, "xyz")

    def test_data_suffix_raises_error(self):
        """Data suffixes should raise error indicating data, not code."""
        with self.assertRaises(DataExtensionError) as ctx:
            detect_language_from_suffix("data.csv")
        self.assertEqual(ctx.exception.extension, "csv")

    def test_json_suffix_raises_data_error(self):
        """JSON suffix should raise data error."""
        with self.assertRaises(DataExtensionError):
            detect_language_from_suffix("data.json")

    def test_txt_suffix_raises_data_error(self):
        """Text suffix should raise data error."""
        with self.assertRaises(DataExtensionError):
            detect_language_from_suffix("data.txt")

    def test_no_suffix_returns_none(self):
        """No suffix returns None."""
        self.assertIsNone(detect_language_from_suffix("nosuffix"))


class TestValidateCid(unittest.TestCase):
    """Test validate_cid function."""

    def test_valid_literal_cid(self):
        """Valid literal CID passes validation."""
        is_valid, error = validate_cid("AAAAAAAA")
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_invalid_format(self):
        """Invalid format fails validation."""
        is_valid, error = validate_cid("invalid")
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)

    def test_too_short(self):
        """Too short CID fails validation."""
        is_valid, error = validate_cid("AAAA")
        self.assertFalse(is_valid)
        self.assertIn("cid", error.lower())

    def test_cid_with_extension(self):
        """CID with extension still validates."""
        is_valid, error = validate_cid("AAAAAAAA.py")
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class TestGetResolutionType(unittest.TestCase):
    """Test get_resolution_type function."""

    def test_sh_suffix_is_execution(self):
        """Bash suffix means execution."""
        self.assertEqual(get_resolution_type("segment.sh", "server"), "execution")

    def test_py_suffix_is_execution(self):
        """Python suffix means execution."""
        self.assertEqual(get_resolution_type("segment.py", "cid"), "execution")

    def test_js_suffix_is_execution(self):
        """JavaScript suffix means execution."""
        self.assertEqual(get_resolution_type("segment.js", "server"), "execution")

    def test_ts_suffix_is_execution(self):
        """TypeScript suffix means execution."""
        self.assertEqual(get_resolution_type("segment.ts", "cid"), "execution")

    def test_clj_suffix_is_execution(self):
        """Clojure suffix means execution."""
        self.assertEqual(get_resolution_type("segment.clj", "server"), "execution")

    def test_cljs_suffix_is_execution(self):
        """ClojureScript suffix means execution."""
        self.assertEqual(get_resolution_type("segment.cljs", "cid"), "execution")

    def test_txt_suffix_is_contents(self):
        """Text suffix means contents."""
        self.assertEqual(get_resolution_type("segment.txt", "cid"), "contents")

    def test_json_suffix_is_contents(self):
        """JSON suffix means contents."""
        self.assertEqual(get_resolution_type("segment.json", "cid"), "contents")

    def test_csv_suffix_is_contents(self):
        """CSV suffix means contents."""
        self.assertEqual(get_resolution_type("segment.csv", "cid"), "contents")

    def test_unrecognized_suffix_is_error(self):
        """Unrecognized extension returns error."""
        self.assertEqual(get_resolution_type("segment.xyz", "cid"), "error")

    def test_no_suffix_server_is_execution(self):
        """No suffix with server type is execution."""
        self.assertEqual(get_resolution_type("servername", "server"), "execution")

    def test_no_suffix_cid_is_execution(self):
        """No suffix with CID type is execution."""
        self.assertEqual(get_resolution_type("AAAAAAAA", "cid"), "execution")

    def test_no_suffix_alias_is_execution(self):
        """No suffix with alias type is execution."""
        self.assertEqual(get_resolution_type("myalias", "alias"), "execution")

    def test_no_suffix_parameter_is_literal(self):
        """No suffix with parameter type is literal."""
        self.assertEqual(get_resolution_type("value", "parameter"), "literal")


class TestResolveSegmentType(unittest.TestCase):
    """Test resolve_segment_type function."""

    @patch("server_execution.segment_analysis.get_server_by_name")
    @patch("server_execution.segment_analysis.find_matching_alias")
    def test_named_server_detection(self, mock_alias, mock_server):
        """Detect segment as named server."""
        mock_server.return_value = MagicMock(enabled=True)
        mock_alias.return_value = None

        result = resolve_segment_type("echo")
        self.assertEqual(result, "server")

    @patch("server_execution.segment_analysis.get_server_by_name")
    @patch("server_execution.segment_analysis.find_matching_alias")
    def test_disabled_server_not_detected(self, mock_alias, mock_server):
        """Disabled server is not detected as server."""
        mock_server.return_value = MagicMock(enabled=False)
        mock_alias.return_value = None

        result = resolve_segment_type("disabled")
        # Should fall through to CID or parameter
        self.assertIn(result, ["cid", "parameter"])

    @patch("server_execution.segment_analysis.get_server_by_name")
    @patch("server_execution.segment_analysis.find_matching_alias")
    def test_alias_detection(self, mock_alias, mock_server):
        """Detect segment as alias."""
        mock_server.return_value = None
        mock_alias.return_value = MagicMock()

        result = resolve_segment_type("myalias")
        self.assertEqual(result, "alias")

    @patch("server_execution.segment_analysis.get_server_by_name")
    @patch("server_execution.segment_analysis.find_matching_alias")
    def test_cid_detection(self, mock_alias, mock_server):
        """Detect segment as CID."""
        mock_server.return_value = None
        mock_alias.return_value = None

        result = resolve_segment_type("AAAAAAAA")
        self.assertEqual(result, "cid")

    @patch("server_execution.segment_analysis.get_server_by_name")
    @patch("server_execution.segment_analysis.find_matching_alias")
    def test_parameter_fallback(self, mock_alias, mock_server):
        """Detect segment as parameter when nothing else matches."""
        mock_server.return_value = None
        mock_alias.return_value = None

        # Use a segment with characters not valid in CIDs (like dots or special chars)
        # or very short segment that won't match CID pattern
        result = resolve_segment_type("hi")
        self.assertEqual(result, "parameter")


class TestCheckChainingSupport(unittest.TestCase):
    """Test check_chaining_support function."""

    def test_python_with_main_supports_chaining(self):
        """Python server with main() supports chaining."""
        definition = "def main(x): return x"
        self.assertTrue(check_chaining_support(definition, "python"))

    def test_python_without_main_no_chaining(self):
        """Python server without main() doesn't support chaining."""
        definition = "def helper(x): return x"
        self.assertFalse(check_chaining_support(definition, "python"))

    def test_bash_supports_chaining(self):
        """Bash scripts support chaining."""
        self.assertTrue(check_chaining_support("echo hello", "bash"))

    def test_javascript_supports_chaining(self):
        """JavaScript scripts support chaining."""
        self.assertTrue(check_chaining_support("console.log('hi')", "javascript"))

    def test_clojure_supports_chaining(self):
        """Clojure scripts support chaining."""
        self.assertTrue(check_chaining_support("(println 'hi')", "clojure"))

    def test_typescript_supports_chaining(self):
        """TypeScript scripts support chaining."""
        self.assertTrue(check_chaining_support("console.log('hi')", "typescript"))


class TestResolveAliases(unittest.TestCase):
    """Test resolve_aliases function."""

    @patch("server_execution.segment_analysis.resolve_alias_target")
    def test_no_alias_returns_empty(self, mock_resolve):
        """Non-alias segment returns empty list."""
        mock_resolve.return_value = None
        result = resolve_aliases("directserver")
        self.assertEqual(result, [])

    @patch("server_execution.segment_analysis.resolve_alias_target")
    def test_single_alias_returned(self, mock_resolve):
        """Single alias resolution tracked."""
        mock_match = MagicMock()
        mock_match.alias = MagicMock(name="myalias")
        mock_match.alias.name = "myalias"

        mock_resolve.side_effect = [
            MagicMock(match=mock_match, target="/server", is_relative=True),
            None,
        ]

        result = resolve_aliases("myalias")
        self.assertEqual(result, ["myalias"])


class TestAnalyzeSegment(unittest.TestCase):
    """Test analyze_segment function."""

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_server_segment_analysis(self, mock_type, mock_info):
        """Analyze server segment."""
        mock_type.return_value = "server"
        mock_info.return_value = {
            "name": "echo",
            "definition_cid": "ABC123",
            "supports_chaining": True,
            "language": "python",
            "parameters": [],
        }

        info = analyze_segment("echo", 0, 2)

        self.assertEqual(info.segment_type, "server")
        self.assertEqual(info.server_name, "echo")
        self.assertEqual(info.implementation_language, "python")
        self.assertTrue(info.supports_chaining)

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_cid_segment_analysis(self, mock_type, mock_info):
        """Analyze CID segment."""
        mock_type.return_value = "cid"
        mock_info.return_value = None

        info = analyze_segment("AAAAAAAA", 1, 2)

        self.assertEqual(info.segment_type, "cid")
        self.assertTrue(info.is_valid_cid)

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_unrecognized_extension_error(self, mock_type, mock_info):
        """Unrecognized extension creates error."""
        mock_type.return_value = "cid"
        mock_info.return_value = None

        info = analyze_segment("data.xyz", 1, 2)

        self.assertEqual(info.resolution_type, "error")
        self.assertTrue(any("unrecognized extension" in e for e in info.errors))

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_chaining_not_supported_error(self, mock_type, mock_info):
        """Python without main in non-last position creates error."""
        mock_type.return_value = "server"
        mock_info.return_value = {
            "name": "no-main",
            "definition_cid": "ABC123",
            "supports_chaining": False,
            "language": "python",
            "parameters": [],
        }

        info = analyze_segment("no-main", 0, 2)  # Not last position

        self.assertFalse(info.supports_chaining)
        self.assertTrue(any("does not support chaining" in e for e in info.errors))


class TestPathSegmentInfo(unittest.TestCase):
    """Test PathSegmentInfo dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        info = PathSegmentInfo(
            segment_text="test",
            segment_type="parameter",
            resolution_type="literal",
        )

        self.assertEqual(info.segment_text, "test")
        self.assertFalse(info.is_valid_cid)
        self.assertEqual(info.aliases_involved, [])
        self.assertEqual(info.errors, [])
        self.assertTrue(info.supports_chaining)
        self.assertFalse(info.executed)


class TestPipelineExecutionResult(unittest.TestCase):
    """Test PipelineExecutionResult dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = PipelineExecutionResult(segments=[])

        self.assertEqual(result.segments, [])
        self.assertIsNone(result.final_output)
        self.assertEqual(result.final_content_type, "text/html")
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)


class TestGetServerInfo(unittest.TestCase):
    """Test get_server_info function."""

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_named_server_info(self, mock_get_server, mock_load_literal):
        """Get info for named server."""
        mock_server = MagicMock()
        mock_server.enabled = True
        mock_server.definition = "def main(x): return x"
        mock_server.definition_cid = "SERVER_CID"
        mock_get_server.return_value = mock_server
        mock_load_literal.return_value = (None, None, None)

        info = get_server_info("echo")

        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "echo")
        self.assertEqual(info["definition_cid"], "SERVER_CID")
        self.assertEqual(info["language"], "python")
        self.assertTrue(info["supports_chaining"])

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_disabled_server_returns_none(self, mock_get_server, mock_load_literal):
        """Disabled server returns None."""
        mock_server = MagicMock()
        mock_server.enabled = False
        mock_get_server.return_value = mock_server
        mock_load_literal.return_value = (None, None, None)

        info = get_server_info("disabled")

        self.assertIsNone(info)

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_cid_literal_server_info(self, mock_get_server, mock_load_literal):
        """Get info for CID-based server."""
        mock_get_server.return_value = None
        mock_load_literal.return_value = (
            "def main(x): return x",  # definition
            None,  # lang_override
            "CID_VALUE",  # normalized_cid
        )

        info = get_server_info("AAAAAAAA")

        self.assertIsNotNone(info)
        self.assertEqual(info["definition_cid"], "CID_VALUE")
        self.assertEqual(info["language"], "python")

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_nonexistent_server_returns_none(self, mock_get_server, mock_load_literal):
        """Nonexistent server returns None."""
        mock_get_server.return_value = None
        mock_load_literal.return_value = (None, None, None)

        info = get_server_info("nonexistent")

        self.assertIsNone(info)

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_server_with_parameters(self, mock_get_server, mock_load_literal):
        """Server info includes parameters."""
        mock_server = MagicMock()
        mock_server.enabled = True
        mock_server.definition = "def main(x, y=None): return x"
        mock_server.definition_cid = "SERVER_CID"
        mock_get_server.return_value = mock_server
        mock_load_literal.return_value = (None, None, None)

        info = get_server_info("echo")

        self.assertIsNotNone(info)
        params = info["parameters"]
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0].name, "x")
        self.assertTrue(params[0].required)
        self.assertEqual(params[1].name, "y")
        self.assertFalse(params[1].required)

    @patch("server_execution.pipeline_execution._load_server_literal")
    @patch("server_execution.segment_analysis.get_server_by_name")
    def test_bash_server_info(self, mock_get_server, mock_load_literal):
        """Get info for bash server."""
        mock_server = MagicMock()
        mock_server.enabled = True
        mock_server.definition = "#!/bin/bash\necho hello"
        mock_server.definition_cid = "BASH_CID"
        mock_get_server.return_value = mock_server
        mock_load_literal.return_value = (None, None, None)

        info = get_server_info("bash-server")

        self.assertIsNotNone(info)
        self.assertEqual(info["language"], "bash")
        self.assertTrue(info["supports_chaining"])


class TestExecutePipeline(unittest.TestCase):
    """Test execute_pipeline function."""

    def test_empty_path_returns_error(self):
        """Empty pipeline path returns error."""
        from server_execution.pipeline_execution import execute_pipeline

        result = execute_pipeline("")

        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Empty pipeline path")
        self.assertEqual(result.segments, [])

    def test_root_path_returns_error(self):
        """Root path only returns error."""
        from server_execution.pipeline_execution import execute_pipeline

        result = execute_pipeline("/")

        self.assertFalse(result.success)

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_single_parameter_segment(self, mock_type, mock_info):
        """Single parameter segment resolves to literal."""
        from server_execution.pipeline_execution import execute_pipeline

        mock_type.return_value = "parameter"
        mock_info.return_value = None

        result = execute_pipeline("/hello")

        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].segment_type, "parameter")
        self.assertEqual(result.segments[0].resolution_type, "literal")

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_error_segment_prevents_execution(self, mock_type, mock_info):
        """Error in segment prevents execution."""
        from server_execution.pipeline_execution import execute_pipeline

        # First segment is server, second has error extension
        mock_type.side_effect = ["server", "cid"]
        mock_info.return_value = None

        result = execute_pipeline("/server/data.xyz")

        # Should have error for unrecognized extension
        self.assertFalse(result.success)
        error_segment = result.segments[1]
        self.assertEqual(error_segment.resolution_type, "error")

    @patch("server_execution.pipeline_execution.get_server_info")
    @patch("server_execution.pipeline_execution.resolve_segment_type")
    def test_multiple_segments_analyzed(self, mock_type, mock_info):
        """Multiple segments are all analyzed."""
        from server_execution.pipeline_execution import execute_pipeline

        mock_type.side_effect = ["server", "server", "parameter"]
        mock_info.return_value = {
            "name": "test",
            "definition_cid": "CID",
            "supports_chaining": True,
            "language": "python",
            "parameters": [],
        }

        result = execute_pipeline("/s1/s2/input")

        self.assertEqual(len(result.segments), 3)


class TestParameterInfo(unittest.TestCase):
    """Test ParameterInfo dataclass."""

    def test_required_parameter(self):
        """Test required parameter."""
        param = ParameterInfo(name="x", required=True, source="path", value="test")

        self.assertEqual(param.name, "x")
        self.assertTrue(param.required)
        self.assertEqual(param.source, "path")
        self.assertEqual(param.value, "test")

    def test_optional_parameter(self):
        """Test optional parameter with defaults."""
        param = ParameterInfo(name="y", required=False)

        self.assertEqual(param.name, "y")
        self.assertFalse(param.required)
        self.assertIsNone(param.source)
        self.assertIsNone(param.value)


class TestDataExtensionHandling(unittest.TestCase):
    """Test handling of data extensions."""

    def test_xml_is_contents(self):
        """XML extension returns contents resolution."""
        self.assertEqual(get_resolution_type("data.xml", "cid"), "contents")

    def test_html_is_contents(self):
        """HTML extension returns contents resolution."""
        self.assertEqual(get_resolution_type("page.html", "cid"), "contents")

    def test_md_is_contents(self):
        """Markdown extension returns contents resolution."""
        self.assertEqual(get_resolution_type("doc.md", "cid"), "contents")


class TestExtensionCaseSensitivity(unittest.TestCase):
    """Test that extensions are case-insensitive."""

    def test_py_uppercase(self):
        """Uppercase .PY works."""
        self.assertEqual(detect_language_from_suffix("script.PY"), "python")

    def test_sh_uppercase(self):
        """Uppercase .SH works."""
        self.assertEqual(detect_language_from_suffix("script.SH"), "bash")

    def test_js_mixed_case(self):
        """Mixed case .Js works."""
        self.assertEqual(detect_language_from_suffix("script.Js"), "javascript")

    def test_json_uppercase_is_contents(self):
        """Uppercase .JSON is contents."""
        self.assertEqual(get_resolution_type("data.JSON", "cid"), "contents")


if __name__ == "__main__":
    unittest.main()
