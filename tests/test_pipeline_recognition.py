"""Unit tests for routes/pipelines.py - Pipeline recognition functions."""

import unittest
from unittest.mock import MagicMock, patch

from routes.pipelines import (
    get_final_extension,
    get_segment_base_and_extension,
    is_pipeline_request,
    parse_pipeline_path,
    should_return_debug_response,
)


class TestParsePipelinePath(unittest.TestCase):
    """Test parse_pipeline_path function."""

    def test_simple_path_segments(self):
        """Parse simple path into segments."""
        result = parse_pipeline_path("/a/b/c")
        self.assertEqual(result, ["a", "b", "c"])

    def test_four_segments(self):
        """Parse path with four segments."""
        result = parse_pipeline_path("/this/has/four/segments")
        self.assertEqual(result, ["this", "has", "four", "segments"])

    def test_empty_segments_filtered(self):
        """Empty segments are filtered out."""
        result = parse_pipeline_path("/a//b/")
        self.assertEqual(result, ["a", "b"])

    def test_url_encoded_segments(self):
        """URL encoded segments are decoded."""
        result = parse_pipeline_path("/hello%20world")
        self.assertEqual(result, ["hello world"])

    def test_segments_with_dots(self):
        """Segments with dots preserved."""
        result = parse_pipeline_path("/server.py/input")
        self.assertEqual(result, ["server.py", "input"])

    def test_empty_path(self):
        """Handle empty path."""
        result = parse_pipeline_path("")
        self.assertEqual(result, [])

    def test_none_path(self):
        """Handle None-like path."""
        result = parse_pipeline_path(None)
        self.assertEqual(result, [])

    def test_single_segment(self):
        """Handle single segment."""
        result = parse_pipeline_path("/single")
        self.assertEqual(result, ["single"])

    def test_root_only(self):
        """Handle root path only."""
        result = parse_pipeline_path("/")
        self.assertEqual(result, [])


class TestGetFinalExtension(unittest.TestCase):
    """Test get_final_extension function."""

    def test_extension_before_query(self):
        """Extract extension before query string."""
        result = get_final_extension("/path/file.json?debug=true")
        self.assertEqual(result, "json")

    def test_no_extension(self):
        """Handle paths without extension."""
        result = get_final_extension("/path/file")
        self.assertIsNone(result)

    def test_multiple_dots(self):
        """Handle multiple dots correctly."""
        result = get_final_extension("/path/file.tar.gz")
        self.assertEqual(result, "gz")

    def test_extension_in_middle_segment(self):
        """Only consider final segment extension."""
        result = get_final_extension("/server.py/input")
        self.assertIsNone(result)

    def test_extension_with_fragment(self):
        """Handle extension with fragment."""
        result = get_final_extension("/path/file.html#section")
        self.assertEqual(result, "html")

    def test_empty_path(self):
        """Handle empty path."""
        result = get_final_extension("")
        self.assertIsNone(result)

    def test_extension_only_final_segment(self):
        """Extension from final segment only."""
        result = get_final_extension("/data.csv/output.json")
        self.assertEqual(result, "json")


class TestShouldReturnDebugResponse(unittest.TestCase):
    """Test should_return_debug_response function."""

    def _mock_request(self, debug_value=None):
        """Create a mock request with the given debug parameter."""
        mock_req = MagicMock()
        if debug_value is not None:
            mock_req.args = {"debug": debug_value}
        else:
            mock_req.args = {}
        return mock_req

    def test_debug_true_returns_true(self):
        """debug=true query param returns True."""
        req = self._mock_request("true")
        self.assertTrue(should_return_debug_response(req))

    def test_debug_false_returns_false(self):
        """debug=false query param returns False."""
        req = self._mock_request("false")
        self.assertFalse(should_return_debug_response(req))

    def test_no_debug_param_returns_false(self):
        """Missing debug param returns False."""
        req = self._mock_request(None)
        self.assertFalse(should_return_debug_response(req))

    def test_debug_1_returns_true(self):
        """debug=1 query param returns True."""
        req = self._mock_request("1")
        self.assertTrue(should_return_debug_response(req))

    def test_debug_yes_returns_true(self):
        """debug=yes query param returns True."""
        req = self._mock_request("yes")
        self.assertTrue(should_return_debug_response(req))

    def test_debug_on_returns_true(self):
        """debug=on query param returns True."""
        req = self._mock_request("on")
        self.assertTrue(should_return_debug_response(req))

    def test_debug_case_insensitive(self):
        """Debug param is case insensitive."""
        self.assertTrue(should_return_debug_response(self._mock_request("TRUE")))
        self.assertTrue(should_return_debug_response(self._mock_request("True")))
        self.assertTrue(should_return_debug_response(self._mock_request("YES")))
        self.assertTrue(should_return_debug_response(self._mock_request("On")))

    def test_debug_0_returns_false(self):
        """debug=0 query param returns False."""
        req = self._mock_request("0")
        self.assertFalse(should_return_debug_response(req))

    def test_debug_no_returns_false(self):
        """debug=no query param returns False."""
        req = self._mock_request("no")
        self.assertFalse(should_return_debug_response(req))

    def test_debug_off_returns_false(self):
        """debug=off query param returns False."""
        req = self._mock_request("off")
        self.assertFalse(should_return_debug_response(req))

    def test_debug_random_value_returns_false(self):
        """debug=random returns False (not in truthy set)."""
        req = self._mock_request("random")
        self.assertFalse(should_return_debug_response(req))


class TestGetSegmentBaseAndExtension(unittest.TestCase):
    """Test get_segment_base_and_extension function."""

    def test_segment_with_extension(self):
        """Split segment with extension."""
        base, ext = get_segment_base_and_extension("script.py")
        self.assertEqual(base, "script")
        self.assertEqual(ext, "py")

    def test_segment_without_extension(self):
        """Handle segment without extension."""
        base, ext = get_segment_base_and_extension("data")
        self.assertEqual(base, "data")
        self.assertIsNone(ext)

    def test_segment_with_multiple_dots(self):
        """Handle segment with multiple dots."""
        base, ext = get_segment_base_and_extension("file.tar.gz")
        self.assertEqual(base, "file.tar")
        self.assertEqual(ext, "gz")

    def test_segment_ending_with_dot(self):
        """Handle segment ending with dot."""
        base, ext = get_segment_base_and_extension("file.")
        self.assertEqual(base, "file")
        self.assertIsNone(ext)


class TestIsPipelineRequest(unittest.TestCase):
    """Test is_pipeline_request function."""

    @patch("routes.pipelines._could_be_executed")
    def test_single_segment_not_pipeline(self, mock_executed):
        """Single path segment is not a pipeline."""
        result = is_pipeline_request("/server")
        self.assertFalse(result)
        # _could_be_executed shouldn't even be called for single segment
        mock_executed.assert_not_called()

    @patch("routes.pipelines._could_be_executed")
    def test_two_segments_with_server_is_pipeline(self, mock_executed):
        """Two segments where first is executable is a pipeline."""
        mock_executed.return_value = True
        result = is_pipeline_request("/server/input")
        self.assertTrue(result)

    @patch("routes.pipelines._could_be_executed")
    def test_two_segments_first_not_executable_not_pipeline(self, mock_executed):
        """Two segments where first is not executable is not a pipeline."""
        mock_executed.return_value = False
        result = is_pipeline_request("/static/path")
        self.assertFalse(result)

    @patch("routes.pipelines._could_be_executed")
    def test_three_level_chain_is_pipeline(self, mock_executed):
        """Three-level chain is a pipeline."""
        mock_executed.return_value = True
        result = is_pipeline_request("/s3/s2/s1")
        self.assertTrue(result)

    def test_empty_path_not_pipeline(self):
        """Empty path is not a pipeline."""
        result = is_pipeline_request("")
        self.assertFalse(result)

    def test_root_path_not_pipeline(self):
        """Root path is not a pipeline."""
        result = is_pipeline_request("/")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
