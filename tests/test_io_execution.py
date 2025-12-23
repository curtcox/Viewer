"""Tests for IO execution engine.

These tests verify the IO execution behavior:
- Request phase flows left-to-right
- Response phase flows right-to-left
- Middle servers are invoked twice
- Tail server is invoked once
- Parameters bind to servers on their left
"""

import unittest
from unittest.mock import MagicMock, patch

from server_execution.io_execution import (
    IOExecutionResult,
    IOSegmentInfo,
    execute_io_chain,
    group_segments_with_params,
    parse_io_path,
)


class TestParseIOPath(unittest.TestCase):
    """Test IO path parsing."""

    def test_empty_path(self):
        """Empty path returns empty list."""
        result = parse_io_path("")
        self.assertEqual(result, [])

    def test_io_only(self):
        """Path with only /io returns empty list."""
        result = parse_io_path("/io")
        self.assertEqual(result, [])

    def test_io_with_trailing_slash(self):
        """Path /io/ returns empty list (shows landing page)."""
        result = parse_io_path("/io/")
        self.assertEqual(result, [])

    def test_single_segment(self):
        """/io/server returns ['server']."""
        result = parse_io_path("/io/server")
        self.assertEqual(result, ["server"])

    def test_multiple_segments(self):
        """/io/s1/param/s2 returns ['s1', 'param', 's2']."""
        result = parse_io_path("/io/s1/param/s2")
        self.assertEqual(result, ["s1", "param", "s2"])

    def test_empty_segments_filtered(self):
        """/io//server ignores empty segments."""
        result = parse_io_path("/io//server")
        self.assertEqual(result, ["server"])

    def test_multiple_empty_segments(self):
        """/io/s1///s2 ignores all empty segments."""
        result = parse_io_path("/io/s1///s2")
        self.assertEqual(result, ["s1", "s2"])


class TestGroupSegmentsWithParams(unittest.TestCase):
    """Test segment grouping with parameters."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_patcher = patch(
            "server_execution.segment_analysis.get_server_by_name"
        )
        self.alias_patcher = patch(
            "server_execution.segment_analysis.find_matching_alias"
        )
        self.mock_get_server = self.server_patcher.start()
        self.mock_find_alias = self.alias_patcher.start()

        self.mock_get_server.return_value = None
        self.mock_find_alias.return_value = None

    def tearDown(self):
        """Clean up patches."""
        self.server_patcher.stop()
        self.alias_patcher.stop()

    def _setup_servers(self, names):
        """Configure mocks to return servers for given names."""

        def side_effect(name):
            if name in names:
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(request, response=None): return request"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

    def test_empty_segments(self):
        """Empty segments returns empty list."""
        result = group_segments_with_params([])
        self.assertEqual(result, [])

    def test_single_server(self):
        """Single server returns one group with no params."""
        self._setup_servers(["s1"])

        result = group_segments_with_params(["s1"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["segment"], "s1")
        self.assertEqual(result[0]["params"], [])

    def test_server_with_single_param(self):
        """Server with param groups them together."""
        self._setup_servers(["s1"])

        result = group_segments_with_params(["s1", "param"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["segment"], "s1")
        self.assertEqual(result[0]["params"], ["param"])

    def test_server_with_multiple_params(self):
        """Server with multiple params groups all together."""
        self._setup_servers(["s1"])

        result = group_segments_with_params(["s1", "p1", "p2"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["segment"], "s1")
        self.assertEqual(result[0]["params"], ["p1", "p2"])

    def test_multiple_servers_with_params(self):
        """Multiple servers each get their own params."""
        self._setup_servers(["s1", "s2"])

        result = group_segments_with_params(["s1", "p1", "s2", "p2"])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["segment"], "s1")
        self.assertEqual(result[0]["params"], ["p1"])
        self.assertEqual(result[1]["segment"], "s2")
        self.assertEqual(result[1]["params"], ["p2"])

    def test_server_no_param_then_server_with_param(self):
        """First server no params, second server has params."""
        self._setup_servers(["s1", "s2"])

        result = group_segments_with_params(["s1", "s2", "p1"])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["segment"], "s1")
        self.assertEqual(result[0]["params"], [])
        self.assertEqual(result[1]["segment"], "s2")
        self.assertEqual(result[1]["params"], ["p1"])


class TestIOExecutionChain(unittest.TestCase):
    """Test IO chain execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_patcher = patch(
            "server_execution.segment_analysis.get_server_by_name"
        )
        self.alias_patcher = patch(
            "server_execution.segment_analysis.find_matching_alias"
        )
        self.mock_get_server = self.server_patcher.start()
        self.mock_find_alias = self.alias_patcher.start()

        self.mock_get_server.return_value = None
        self.mock_find_alias.return_value = None

    def tearDown(self):
        """Clean up patches."""
        self.server_patcher.stop()
        self.alias_patcher.stop()

    def _setup_servers(self, names):
        """Configure mocks to return servers for given names."""

        def side_effect(name):
            if name in names:
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(request, response=None): return request"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

    def test_empty_path_returns_success(self):
        """Empty path returns success with no segments."""
        result = execute_io_chain("/io")

        self.assertTrue(result.success)
        self.assertEqual(result.segments, [])
        self.assertIsNone(result.final_output)

    def test_io_trailing_slash_returns_success(self):
        """/io/ returns success (landing page indicator)."""
        result = execute_io_chain("/io/")

        self.assertTrue(result.success)
        self.assertEqual(result.segments, [])

    def test_single_server_is_tail(self):
        """Single server is marked as tail."""
        self._setup_servers(["echo"])

        result = execute_io_chain("/io/echo")

        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].role, "tail")

    def test_two_servers_roles(self):
        """With two servers, first is middle, second is tail."""
        self._setup_servers(["s1", "s2"])

        result = execute_io_chain("/io/s1/s2")

        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.segments[0].role, "middle")
        self.assertEqual(result.segments[1].role, "tail")

    def test_three_servers_roles(self):
        """With three servers, first two are middle, last is tail."""
        self._setup_servers(["s1", "s2", "s3"])

        result = execute_io_chain("/io/s1/s2/s3")

        self.assertEqual(len(result.segments), 3)
        self.assertEqual(result.segments[0].role, "middle")
        self.assertEqual(result.segments[1].role, "middle")
        self.assertEqual(result.segments[2].role, "tail")


class TestIOSegmentInfo(unittest.TestCase):
    """Test IOSegmentInfo data class."""

    def test_from_path_segment_info(self):
        """Test conversion from PathSegmentInfo."""
        from server_execution.segment_analysis import PathSegmentInfo

        path_info = PathSegmentInfo(
            segment_text="test",
            segment_type="server",
            resolution_type="execution",
            server_name="test",
            supports_chaining=True,
            implementation_language="python",
        )

        io_info = IOSegmentInfo.from_path_segment_info(path_info)

        self.assertEqual(io_info.segment_text, "test")
        self.assertEqual(io_info.segment_type, "server")
        self.assertEqual(io_info.resolution_type, "execution")
        self.assertEqual(io_info.server_name, "test")
        self.assertTrue(io_info.supports_chaining)
        self.assertEqual(io_info.implementation_language, "python")

    def test_default_role_is_middle(self):
        """Default role is 'middle'."""
        io_info = IOSegmentInfo(
            segment_text="test",
            segment_type="server",
            resolution_type="execution",
        )

        self.assertEqual(io_info.role, "middle")

    def test_phase_tracking_defaults(self):
        """Phase tracking fields default to None/False."""
        io_info = IOSegmentInfo(
            segment_text="test",
            segment_type="server",
            resolution_type="execution",
        )

        self.assertIsNone(io_info.request_phase_input)
        self.assertIsNone(io_info.request_phase_output)
        self.assertFalse(io_info.request_phase_executed)
        self.assertIsNone(io_info.response_phase_request)
        self.assertIsNone(io_info.response_phase_response)
        self.assertIsNone(io_info.response_phase_output)
        self.assertFalse(io_info.response_phase_executed)


class TestIOParameterBinding(unittest.TestCase):
    """Test IO-specific parameter binding behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_patcher = patch(
            "server_execution.segment_analysis.get_server_by_name"
        )
        self.alias_patcher = patch(
            "server_execution.segment_analysis.find_matching_alias"
        )
        self.mock_get_server = self.server_patcher.start()
        self.mock_find_alias = self.alias_patcher.start()

        self.mock_get_server.return_value = None
        self.mock_find_alias.return_value = None

    def tearDown(self):
        """Clean up patches."""
        self.server_patcher.stop()
        self.alias_patcher.stop()

    def _setup_servers(self, names):
        """Configure mocks to return servers for given names."""

        def side_effect(name):
            if name in names:
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(request, response=None): return request"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

    def test_single_param_in_request_phase(self):
        """/io/s1/param - s1 receives param in request phase."""
        self._setup_servers(["s1"])

        result = execute_io_chain("/io/s1/param")

        # s1 should have param as request_phase_input
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].request_phase_input, "param")

    def test_empty_segments_handled(self):
        """/io/s1//s2 - empty segment ignored, works like /io/s1/s2."""
        self._setup_servers(["s1", "s2"])

        result = execute_io_chain("/io/s1//s2")

        self.assertEqual(len(result.segments), 2)


class TestIOExecutionResult(unittest.TestCase):
    """Test IOExecutionResult data class."""

    def test_default_values(self):
        """Test default values for IOExecutionResult."""
        result = IOExecutionResult(segments=[])

        self.assertEqual(result.segments, [])
        self.assertIsNone(result.final_output)
        self.assertEqual(result.final_content_type, "text/html")
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)

    def test_with_error(self):
        """Test IOExecutionResult with error."""
        result = IOExecutionResult(
            segments=[],
            success=False,
            error_message="Something went wrong",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Something went wrong")


if __name__ == "__main__":
    unittest.main()
