#!/usr/bin/env python3
"""
Test script for server definition history functionality.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime, timezone

# Import route helper for testing
from routes.servers import get_server_definition_history


class TestServerHistory(unittest.TestCase):
    """Test server definition history functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.server_name = "test_server"

    @patch("routes.servers.get_uploads")
    def test_get_server_definition_history_empty(self, mock_get_uploads):
        """Test getting history when no CIDs exist"""
        # Mock empty query result
        mock_get_uploads.return_value = []

        history = get_server_definition_history(self.server_name)

        self.assertEqual(history, [])

    @patch("routes.servers.get_uploads")
    def test_get_server_definition_history_with_data(self, mock_get_uploads):
        """Test getting history with actual server definitions"""
        # Create mock CID objects
        mock_cid1 = Mock()
        mock_cid1.path = "cid123"
        mock_cid1.created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_cid1.file_data = json.dumps(
            {"test_server": "print('version 1')", "other_server": "print('other')"}
        ).encode("utf-8")

        mock_cid2 = Mock()
        mock_cid2.path = "cid456"
        mock_cid2.created_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        mock_cid2.file_data = json.dumps(
            {
                "test_server": "print('version 2')",
                "other_server": "print('other updated')",
            }
        ).encode("utf-8")

        # Mock query to return CIDs in reverse chronological order (newest first)
        mock_get_uploads.return_value = [mock_cid2, mock_cid1]

        history = get_server_definition_history(self.server_name)

        # Should return 2 entries, newest first
        self.assertEqual(len(history), 2)

        # Check first entry (newest)
        self.assertEqual(history[0]["snapshot_cid"], "cid456")
        self.assertEqual(history[0]["definition"], "print('version 2')")
        self.assertTrue(history[0]["is_current"])
        self.assertEqual(
            history[0]["created_at"],
            datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        )

        # Check second entry (older)
        self.assertEqual(history[1]["snapshot_cid"], "cid123")
        self.assertEqual(history[1]["definition"], "print('version 1')")
        self.assertFalse(history[1]["is_current"])
        self.assertEqual(
            history[1]["created_at"],
            datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

    @patch("routes.servers.get_uploads")
    def test_get_server_definition_history_ignores_invalid_json(self, mock_get_uploads):
        """Test that invalid JSON CIDs are ignored"""
        # Create mock CID with invalid JSON
        mock_cid_invalid = Mock()
        mock_cid_invalid.path = "cid_invalid"
        mock_cid_invalid.created_at = datetime(
            2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        mock_cid_invalid.file_data = b"invalid json content"

        # Create mock CID with valid JSON
        mock_cid_valid = Mock()
        mock_cid_valid.path = "cid_valid"
        mock_cid_valid.created_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        mock_cid_valid.file_data = json.dumps({"test_server": "print('valid')"}).encode(
            "utf-8"
        )

        mock_get_uploads.return_value = [mock_cid_valid, mock_cid_invalid]

        history = get_server_definition_history(self.server_name)

        # Should only return the valid entry
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["snapshot_cid"], "cid_valid")
        self.assertEqual(history[0]["definition"], "print('valid')")

    @patch("routes.servers.get_uploads")
    def test_get_server_definition_history_server_not_in_cid(self, mock_get_uploads):
        """Test that CIDs without the requested server are ignored"""
        # Create mock CID that doesn't contain our server
        mock_cid = Mock()
        mock_cid.path = "cid123"
        mock_cid.created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_cid.file_data = json.dumps(
            {"other_server": "print('other')", "another_server": "print('another')"}
        ).encode("utf-8")

        mock_get_uploads.return_value = [mock_cid]

        history = get_server_definition_history(self.server_name)

        # Should return empty list since our server isn't in any CID
        self.assertEqual(history, [])


if __name__ == "__main__":
    unittest.main()
