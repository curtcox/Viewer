"""Tests for pipeline parameter binding behavior.

These tests verify that pipeline parameters bind correctly to servers:
- Parameters appear to the RIGHT of the server they configure
- Parameters bind to the server on their LEFT

This behavior is shared between pipeline execution and io execution.
"""

import unittest
from unittest.mock import MagicMock, patch

from server_execution.segment_analysis import (
    analyze_segment,
    resolve_segment_type,
)


class TestPipelineParameterBinding(unittest.TestCase):
    """Test parameter binding in pipeline execution."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the database calls to avoid needing actual database
        self.server_patcher = patch(
            "server_execution.segment_analysis.get_server_by_name"
        )
        self.alias_patcher = patch(
            "server_execution.segment_analysis.find_matching_alias"
        )
        self.mock_get_server = self.server_patcher.start()
        self.mock_find_alias = self.alias_patcher.start()

        # Default: no servers or aliases found
        self.mock_get_server.return_value = None
        self.mock_find_alias.return_value = None

    def tearDown(self):
        """Clean up patches."""
        self.server_patcher.stop()
        self.alias_patcher.stop()

    def _setup_server(self, name: str):
        """Configure mock to return a server for the given name."""

        def side_effect(server_name):
            if server_name == name:
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(input): return input"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

    def test_single_param_binds_to_left_server(self):
        """Test that /server/param passes param to server.

        In /echo/hello:
        - 'echo' is the server
        - 'hello' is a parameter that should be passed to echo
        """
        self._setup_server("echo")

        # Analyze 'echo' - should be a server
        echo_info = analyze_segment("echo", 0, 2)
        self.assertEqual(echo_info.segment_type, "server")

        # Analyze 'hello' - should be a parameter (not a server)
        hello_info = analyze_segment("hello", 1, 2)
        self.assertEqual(hello_info.segment_type, "parameter")

    def test_param_position_matters(self):
        """Test that /s1/s2/param means s2 gets param, s1 gets s2's output.

        In pipeline right-to-left execution:
        - param is the rightmost, executed first (returns literal)
        - s2 receives param as input
        - s1 receives s2's output
        """
        # Setup both s1 and s2 as servers
        def side_effect(name):
            if name in ("s1", "s2"):
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(input): return input"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

        s1_info = analyze_segment("s1", 0, 3)
        s2_info = analyze_segment("s2", 1, 3)
        param_info = analyze_segment("param", 2, 3)

        self.assertEqual(s1_info.segment_type, "server")
        self.assertEqual(s2_info.segment_type, "server")
        self.assertEqual(param_info.segment_type, "parameter")

    def test_multiple_adjacent_params(self):
        """Test that /server/p1/p2 passes both p1 and p2 to server.

        In this case, both p1 and p2 are parameters to the right of server.
        """
        self._setup_server("server")

        server_info = analyze_segment("server", 0, 3)
        p1_info = analyze_segment("p1", 1, 3)
        p2_info = analyze_segment("p2", 2, 3)

        self.assertEqual(server_info.segment_type, "server")
        self.assertEqual(p1_info.segment_type, "parameter")
        self.assertEqual(p2_info.segment_type, "parameter")

    def test_params_between_servers(self):
        """Test that /s1/p1/s2/p2 correctly binds params to adjacent servers.

        - p1 binds to s1 (p1 is to the right of s1)
        - p2 binds to s2 (p2 is to the right of s2)
        """
        # Setup both s1 and s2 as servers
        def side_effect(name):
            if name in ("s1", "s2"):
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(input): return input"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

        s1_info = analyze_segment("s1", 0, 4)
        p1_info = analyze_segment("p1", 1, 4)
        s2_info = analyze_segment("s2", 2, 4)
        p2_info = analyze_segment("p2", 3, 4)

        self.assertEqual(s1_info.segment_type, "server")
        self.assertEqual(p1_info.segment_type, "parameter")
        self.assertEqual(s2_info.segment_type, "server")
        self.assertEqual(p2_info.segment_type, "parameter")

    def test_param_not_to_right_server(self):
        """Test that /s1/param/s2 means param goes to s1, NOT s2.

        The param is to the right of s1, so it binds to s1.
        s2 receives s1's output (which processed param).
        """
        # Setup both s1 and s2 as servers
        def side_effect(name):
            if name in ("s1", "s2"):
                mock_server = MagicMock()
                mock_server.enabled = True
                mock_server.definition = "def main(input): return input"
                mock_server.definition_cid = f"cid_{name}"
                return mock_server
            return None

        self.mock_get_server.side_effect = side_effect

        s1_info = analyze_segment("s1", 0, 3)
        param_info = analyze_segment("param", 1, 3)
        s2_info = analyze_segment("s2", 2, 3)

        # param is NOT a server, so it's a parameter for s1
        self.assertEqual(s1_info.segment_type, "server")
        self.assertEqual(param_info.segment_type, "parameter")
        self.assertEqual(s2_info.segment_type, "server")

    def test_rightmost_is_input(self):
        """Test that /echo/hello means echo receives literal 'hello'.

        The rightmost segment is executed first in pipeline mode.
        If it's a parameter (literal), its value is used as input.
        """
        self._setup_server("echo")

        hello_info = analyze_segment("hello", 1, 2)

        # 'hello' should be recognized as a parameter
        self.assertEqual(hello_info.segment_type, "parameter")
        # Resolution type should be 'literal' for parameters
        self.assertEqual(hello_info.resolution_type, "literal")


class TestSegmentTypeResolution(unittest.TestCase):
    """Test segment type resolution priority."""

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

    def test_server_takes_priority(self):
        """Named server takes priority over alias, CID, and parameter."""
        mock_server = MagicMock()
        mock_server.enabled = True
        self.mock_get_server.return_value = mock_server

        result = resolve_segment_type("myserver")
        self.assertEqual(result, "server")

    def test_alias_takes_priority_over_cid(self):
        """Alias takes priority over CID."""
        self.mock_find_alias.return_value = MagicMock()

        result = resolve_segment_type("myalias")
        self.assertEqual(result, "alias")

    def test_disabled_server_not_matched(self):
        """Disabled server should not be matched as 'server' type."""
        mock_server = MagicMock()
        mock_server.enabled = False
        self.mock_get_server.return_value = mock_server

        result = resolve_segment_type("disabled")
        # Should fall through to parameter since server is disabled
        self.assertEqual(result, "parameter")

    def test_unknown_segment_is_parameter(self):
        """Unknown segment (not server, alias, or CID) should be parameter."""
        result = resolve_segment_type("unknown_thing")
        self.assertEqual(result, "parameter")


if __name__ == "__main__":
    unittest.main()
