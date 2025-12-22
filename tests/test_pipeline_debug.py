"""Unit tests for server_execution/pipeline_debug.py."""

import json
import unittest

from server_execution.pipeline_debug import (
    format_debug_html,
    format_debug_json,
    format_debug_response,
    format_debug_text,
    parameter_info_to_dict,
    result_to_dict,
    segment_info_to_dict,
)
from server_execution.pipeline_execution import (
    ParameterInfo,
    PathSegmentInfo,
    PipelineExecutionResult,
)


class TestParameterInfoToDict(unittest.TestCase):
    """Test parameter_info_to_dict function."""

    def test_basic_conversion(self):
        """Convert basic parameter info."""
        param = ParameterInfo(name="x", required=True, source="path", value="test")
        result = parameter_info_to_dict(param)

        self.assertEqual(result["name"], "x")
        self.assertTrue(result["required"])
        self.assertEqual(result["source"], "path")
        self.assertEqual(result["value"], "test")

    def test_optional_parameter(self):
        """Convert optional parameter with no source."""
        param = ParameterInfo(name="y", required=False)
        result = parameter_info_to_dict(param)

        self.assertEqual(result["name"], "y")
        self.assertFalse(result["required"])
        self.assertIsNone(result["source"])
        self.assertIsNone(result["value"])


class TestSegmentInfoToDict(unittest.TestCase):
    """Test segment_info_to_dict function."""

    def test_basic_segment(self):
        """Convert basic segment info."""
        segment = PathSegmentInfo(
            segment_text="test",
            segment_type="parameter",
            resolution_type="literal",
        )
        result = segment_info_to_dict(segment)

        self.assertEqual(result["segment_text"], "test")
        self.assertEqual(result["segment_type"], "parameter")
        self.assertEqual(result["resolution_type"], "literal")
        self.assertFalse(result["is_valid_cid"])
        self.assertEqual(result["aliases_involved"], [])
        self.assertEqual(result["errors"], [])

    def test_server_segment(self):
        """Convert server segment info."""
        segment = PathSegmentInfo(
            segment_text="echo",
            segment_type="server",
            resolution_type="execution",
            server_name="echo",
            implementation_language="python",
            supports_chaining=True,
            server_definition_cid="ABC123",
        )
        result = segment_info_to_dict(segment)

        self.assertEqual(result["segment_type"], "server")
        self.assertEqual(result["resolution_type"], "execution")
        self.assertEqual(result["server_name"], "echo")
        self.assertEqual(result["implementation_language"], "python")
        self.assertTrue(result["supports_chaining"])
        self.assertEqual(result["server_definition_cid"], "ABC123")

    def test_segment_with_parameters(self):
        """Convert segment with parameters."""
        segment = PathSegmentInfo(
            segment_text="server",
            segment_type="server",
            resolution_type="execution",
            input_parameters=[
                ParameterInfo(name="x", required=True, source="path", value="val1"),
                ParameterInfo(name="y", required=False),
            ],
        )
        result = segment_info_to_dict(segment)

        self.assertEqual(len(result["input_parameters"]), 2)
        self.assertEqual(result["input_parameters"][0]["name"], "x")
        self.assertEqual(result["input_parameters"][1]["name"], "y")

    def test_segment_with_errors(self):
        """Convert segment with errors."""
        segment = PathSegmentInfo(
            segment_text="bad.xyz",
            segment_type="parameter",
            resolution_type="error",
            errors=["unrecognized extension: xyz", "another error"],
        )
        result = segment_info_to_dict(segment)

        self.assertEqual(result["resolution_type"], "error")
        self.assertEqual(len(result["errors"]), 2)
        self.assertIn("unrecognized extension: xyz", result["errors"])

    def test_segment_with_aliases(self):
        """Convert segment with alias chain."""
        segment = PathSegmentInfo(
            segment_text="myalias",
            segment_type="alias",
            resolution_type="execution",
            aliases_involved=["myalias", "intermediate", "final"],
        )
        result = segment_info_to_dict(segment)

        self.assertEqual(len(result["aliases_involved"]), 3)
        self.assertEqual(result["aliases_involved"][0], "myalias")

    def test_segment_with_intermediate_output(self):
        """Convert segment with execution output."""
        segment = PathSegmentInfo(
            segment_text="processor",
            segment_type="server",
            resolution_type="execution",
            executed=True,
            input_value="input data",
            intermediate_output="processed output",
            intermediate_content_type="text/plain",
        )
        result = segment_info_to_dict(segment)

        self.assertTrue(result["executed"])
        self.assertEqual(result["input_value"], "input data")
        self.assertEqual(result["intermediate_output"], "processed output")
        self.assertEqual(result["intermediate_content_type"], "text/plain")


class TestResultToDict(unittest.TestCase):
    """Test result_to_dict function."""

    def test_empty_result(self):
        """Convert empty result."""
        result = PipelineExecutionResult(segments=[])
        d = result_to_dict(result)

        self.assertEqual(d["segments"], [])
        self.assertIsNone(d["final_output"])
        self.assertEqual(d["final_content_type"], "text/html")
        self.assertTrue(d["success"])
        self.assertIsNone(d["error_message"])

    def test_result_with_segments(self):
        """Convert result with segments."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="server",
                    segment_type="server",
                    resolution_type="execution",
                ),
                PathSegmentInfo(
                    segment_text="input",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
            ],
            final_output="final result",
            final_content_type="text/plain",
            success=True,
        )
        d = result_to_dict(result)

        self.assertEqual(len(d["segments"]), 2)
        self.assertEqual(d["final_output"], "final result")
        self.assertEqual(d["final_content_type"], "text/plain")
        self.assertTrue(d["success"])

    def test_failed_result(self):
        """Convert failed result with error message."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="bad",
                    segment_type="server",
                    resolution_type="error",
                    errors=["server not found"],
                ),
            ],
            success=False,
            error_message="Pipeline execution had errors",
        )
        d = result_to_dict(result)

        self.assertFalse(d["success"])
        self.assertEqual(d["error_message"], "Pipeline execution had errors")


class TestFormatDebugJson(unittest.TestCase):
    """Test format_debug_json function."""

    def test_json_content_type(self):
        """JSON response has correct content type."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_json(result)

        self.assertEqual(response.mimetype, "application/json")

    def test_json_is_valid(self):
        """Response body is valid JSON."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="test",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
            ]
        )
        response = format_debug_json(result)
        data = json.loads(response.get_data(as_text=True))

        self.assertIn("segments", data)
        self.assertIn("success", data)

    def test_json_includes_all_fields(self):
        """JSON includes all segment fields."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="server",
                    segment_type="server",
                    resolution_type="execution",
                    server_name="test-server",
                    implementation_language="python",
                    executed=True,
                    intermediate_output="output",
                ),
            ],
            final_output="final",
            success=True,
        )
        response = format_debug_json(result)
        data = json.loads(response.get_data(as_text=True))

        seg = data["segments"][0]
        self.assertEqual(seg["segment_text"], "server")
        self.assertEqual(seg["segment_type"], "server")
        self.assertEqual(seg["resolution_type"], "execution")
        self.assertEqual(seg["server_name"], "test-server")
        self.assertEqual(seg["implementation_language"], "python")
        self.assertTrue(seg["executed"])
        self.assertEqual(seg["intermediate_output"], "output")


class TestFormatDebugHtml(unittest.TestCase):
    """Test format_debug_html function."""

    def test_html_content_type(self):
        """HTML response has correct content type."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_html(result)

        self.assertEqual(response.mimetype, "text/html")

    def test_html_contains_doctype(self):
        """HTML starts with DOCTYPE."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertTrue(html.strip().startswith("<!DOCTYPE html>"))

    def test_html_shows_segment_count(self):
        """HTML shows segment count."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="a",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
                PathSegmentInfo(
                    segment_text="b",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
            ]
        )
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertIn("Segments (2)", html)

    def test_html_shows_segment_text(self):
        """HTML displays segment text."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="my-segment",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
            ]
        )
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertIn("my-segment", html)

    def test_html_escapes_special_chars(self):
        """HTML escapes special characters."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="<script>alert('xss')</script>",
                    segment_type="parameter",
                    resolution_type="literal",
                ),
            ]
        )
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_html_shows_errors(self):
        """HTML displays segment errors."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="bad",
                    segment_type="parameter",
                    resolution_type="error",
                    errors=["something went wrong"],
                ),
            ]
        )
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertIn("something went wrong", html)

    def test_html_shows_success_status(self):
        """HTML shows success status."""
        result = PipelineExecutionResult(segments=[], success=True)
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertIn("Success", html)

    def test_html_shows_failure_status(self):
        """HTML shows failure status."""
        result = PipelineExecutionResult(
            segments=[], success=False, error_message="Failed"
        )
        response = format_debug_html(result)
        html = response.get_data(as_text=True)

        self.assertIn("Failed", html)


class TestFormatDebugText(unittest.TestCase):
    """Test format_debug_text function."""

    def test_text_content_type(self):
        """Plain text response has correct content type."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_text(result)

        self.assertEqual(response.mimetype, "text/plain")

    def test_text_shows_header(self):
        """Plain text starts with header."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_text(result)
        text = response.get_data(as_text=True)

        self.assertIn("PIPELINE DEBUG", text)

    def test_text_shows_status(self):
        """Plain text shows status."""
        result = PipelineExecutionResult(segments=[], success=True)
        response = format_debug_text(result)
        text = response.get_data(as_text=True)

        self.assertIn("Status: SUCCESS", text)

    def test_text_shows_failure(self):
        """Plain text shows failure status."""
        result = PipelineExecutionResult(segments=[], success=False)
        response = format_debug_text(result)
        text = response.get_data(as_text=True)

        self.assertIn("Status: FAILED", text)

    def test_text_shows_segment_info(self):
        """Plain text shows segment information."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="server",
                    segment_type="server",
                    resolution_type="execution",
                    implementation_language="python",
                ),
            ]
        )
        response = format_debug_text(result)
        text = response.get_data(as_text=True)

        self.assertIn("Segment 0: server", text)
        self.assertIn("Type:", text)
        self.assertIn("server", text)
        self.assertIn("Language:", text)
        self.assertIn("python", text)

    def test_text_shows_errors(self):
        """Plain text shows errors."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="bad",
                    segment_type="parameter",
                    resolution_type="error",
                    errors=["error one", "error two"],
                ),
            ]
        )
        response = format_debug_text(result)
        text = response.get_data(as_text=True)

        self.assertIn("Errors:", text)
        self.assertIn("error one", text)
        self.assertIn("error two", text)


class TestFormatDebugResponse(unittest.TestCase):
    """Test format_debug_response function."""

    def test_default_is_json(self):
        """Default format is JSON."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result)

        self.assertEqual(response.mimetype, "application/json")

    def test_none_format_is_json(self):
        """None format defaults to JSON."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, None)

        self.assertEqual(response.mimetype, "application/json")

    def test_json_format(self):
        """Explicit JSON format returns JSON."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, "json")

        self.assertEqual(response.mimetype, "application/json")

    def test_html_format(self):
        """HTML format returns HTML."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, "html")

        self.assertEqual(response.mimetype, "text/html")

    def test_txt_format(self):
        """TXT format returns plain text."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, "txt")

        self.assertEqual(response.mimetype, "text/plain")

    def test_text_format(self):
        """TEXT format returns plain text."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, "text")

        self.assertEqual(response.mimetype, "text/plain")

    def test_case_insensitive_format(self):
        """Format is case insensitive."""
        result = PipelineExecutionResult(segments=[])

        self.assertEqual(
            format_debug_response(result, "JSON").mimetype, "application/json"
        )
        self.assertEqual(format_debug_response(result, "HTML").mimetype, "text/html")
        self.assertEqual(format_debug_response(result, "TXT").mimetype, "text/plain")

    def test_unknown_format_defaults_to_json(self):
        """Unknown format defaults to JSON."""
        result = PipelineExecutionResult(segments=[])
        response = format_debug_response(result, "unknown")

        self.assertEqual(response.mimetype, "application/json")


class TestDebugIncludesAllFields(unittest.TestCase):
    """Test that debug responses include all expected fields."""

    def _create_full_segment(self) -> PathSegmentInfo:
        """Create a segment with all fields populated."""
        return PathSegmentInfo(
            segment_text="full-segment",
            segment_type="server",
            resolution_type="execution",
            is_valid_cid=False,
            cid_validation_error=None,
            aliases_involved=["alias1"],
            server_name="full-server",
            server_definition_cid="DEF123",
            supports_chaining=True,
            implementation_language="python",
            input_parameters=[
                ParameterInfo(name="x", required=True, source="path", value="val"),
            ],
            parameter_values={"x": "val"},
            executed=True,
            input_value="input data",
            intermediate_output="output data",
            intermediate_content_type="text/plain",
            server_invocation_cid="INV456",
            errors=[],
        )

    def test_json_has_all_fields(self):
        """JSON includes all segment fields."""
        segment = self._create_full_segment()
        result = PipelineExecutionResult(
            segments=[segment], final_output="final", success=True
        )
        response = format_debug_json(result)
        data = json.loads(response.get_data(as_text=True))
        seg = data["segments"][0]

        self.assertEqual(seg["segment_text"], "full-segment")
        self.assertEqual(seg["segment_type"], "server")
        self.assertEqual(seg["resolution_type"], "execution")
        self.assertFalse(seg["is_valid_cid"])
        self.assertIsNone(seg["cid_validation_error"])
        self.assertEqual(seg["aliases_involved"], ["alias1"])
        self.assertEqual(seg["server_name"], "full-server")
        self.assertEqual(seg["server_definition_cid"], "DEF123")
        self.assertTrue(seg["supports_chaining"])
        self.assertEqual(seg["implementation_language"], "python")
        self.assertEqual(len(seg["input_parameters"]), 1)
        self.assertEqual(seg["parameter_values"], {"x": "val"})
        self.assertTrue(seg["executed"])
        self.assertEqual(seg["input_value"], "input data")
        self.assertEqual(seg["intermediate_output"], "output data")
        self.assertEqual(seg["intermediate_content_type"], "text/plain")
        self.assertEqual(seg["server_invocation_cid"], "INV456")
        self.assertEqual(seg["errors"], [])


class TestDebugShowsIntermediateOutputs(unittest.TestCase):
    """Test that debug shows intermediate outputs per segment."""

    def test_each_segment_has_output(self):
        """Each segment has intermediate_output field."""
        result = PipelineExecutionResult(
            segments=[
                PathSegmentInfo(
                    segment_text="s1",
                    segment_type="server",
                    resolution_type="execution",
                    intermediate_output="output1",
                ),
                PathSegmentInfo(
                    segment_text="s2",
                    segment_type="server",
                    resolution_type="execution",
                    intermediate_output="output2",
                ),
            ],
            final_output="output1",
        )
        response = format_debug_json(result)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(data["segments"][0]["intermediate_output"], "output1")
        self.assertEqual(data["segments"][1]["intermediate_output"], "output2")
        self.assertEqual(data["final_output"], "output1")


if __name__ == "__main__":
    unittest.main()
