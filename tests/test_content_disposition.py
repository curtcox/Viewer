#!/usr/bin/env python3
"""
Simple test for content disposition header logic in serve_cid_content function.
This test focuses on the path parsing logic without requiring the full Flask app.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock


def extract_filename_from_path(path):
    """
    Extract filename from CID path for content disposition header.

    Rules:
    - /{CID} -> no filename (no content disposition)
    - /{CID}.{ext} -> no filename (no content disposition)
    - /{CID}.{filename}.{ext} -> filename = {filename}.{ext}
    """
    # Remove leading slash
    if path.startswith("/"):
        path = path[1:]

    # Handle empty or invalid paths
    if not path or path in [".", ".."]:
        return None

    # Split by dots
    parts = path.split(".")

    # Need at least 3 parts for filename: CID.filename.ext
    if len(parts) < 3:
        return None

    # First part is CID, rest form the filename
    filename_parts = parts[1:]
    filename = ".".join(filename_parts)

    return filename


class TestContentDispositionLogic(unittest.TestCase):
    """Test the logic for determining when to set content disposition headers"""

    def test_cid_only_no_filename(self):
        """Test /{CID} - should return None (no content disposition)"""
        test_cases = [
            "/bafybeihelloworld123456789012345678901234567890123456",
            "/abc123",
            "/short",
        ]

        for path in test_cases:
            with self.subTest(path=path):
                result = extract_filename_from_path(path)
                self.assertIsNone(result, f"Path {path} should not have filename")

    def test_cid_with_extension_no_filename(self):
        """Test /{CID}.{ext} - should return None (no content disposition)"""
        test_cases = [
            "/bafybeihelloworld123456789012345678901234567890123456.txt",
            "/bafybeihelloworld123456789012345678901234567890123456.html",
            "/bafybeihelloworld123456789012345678901234567890123456.json",
            "/abc123.pdf",
        ]

        for path in test_cases:
            with self.subTest(path=path):
                result = extract_filename_from_path(path)
                self.assertIsNone(result, f"Path {path} should not have filename")

    def test_cid_with_filename_returns_filename(self):
        """Test /{CID}.{filename}.{ext} - should return filename.ext"""
        test_cases = [
            (
                "/bafybeihelloworld123456789012345678901234567890123456.document.txt",
                "document.txt",
            ),
            (
                "/bafybeihelloworld123456789012345678901234567890123456.report.pdf",
                "report.pdf",
            ),
            (
                "/bafybeihelloworld123456789012345678901234567890123456.data.json",
                "data.json",
            ),
            (
                "/bafybeihelloworld123456789012345678901234567890123456.page.html",
                "page.html",
            ),
            ("/abc123.myfile.csv", "myfile.csv"),
        ]

        for path, expected_filename in test_cases:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_path(path)
                self.assertEqual(result, expected_filename)

    def test_multiple_dots_in_filename(self):
        """Test /{CID}.{filename.with.dots}.{ext} - should handle multiple dots"""
        test_cases = [
            (
                "/bafybeihelloworld123456789012345678901234567890123456.my.data.file.txt",
                "my.data.file.txt",
            ),
            (
                "/bafybeihelloworld123456789012345678901234567890123456.version.1.2.3.json",
                "version.1.2.3.json",
            ),
            ("/abc123.backup.2024.01.15.sql", "backup.2024.01.15.sql"),
            ("/cid.a.b.c.d.e", "a.b.c.d.e"),
        ]

        for path, expected_filename in test_cases:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_path(path)
                self.assertEqual(result, expected_filename)

    def test_edge_cases(self):
        """Test edge cases"""
        test_cases = [
            ("", None),  # Empty path
            ("/", None),  # Just slash
            ("/.", None),  # Just dot
            ("/..", None),  # Two dots
            ("/a.b.c", "b.c"),  # Short CID but valid pattern
        ]

        for path, expected in test_cases:
            with self.subTest(path=path, expected=expected):
                result = extract_filename_from_path(path)
                self.assertEqual(result, expected)


def mock_serve_cid_content_with_disposition(cid_content, path):
    """
    Mock version of serve_cid_content that includes content disposition logic
    """
    # Check if file_data is None (corrupted or missing data)
    if cid_content is None or cid_content.file_data is None:
        return None

    # Extract CID from path (remove leading slash)
    # cid = path[1:] if path.startswith('/') else path  # Not used in this test

    # Mock response object
    response = Mock()
    response.headers = {}

    # Determine MIME type from URL extension (existing logic)
    content_type = "text/plain"  # Simplified for test

    # Extract filename for content disposition
    filename = extract_filename_from_path(path)
    if filename:
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    # Set other headers (simplified)
    response.headers["Content-Type"] = content_type
    response.headers["Content-Length"] = len(cid_content.file_data)

    return response


class TestMockServeFunction(unittest.TestCase):
    """Test the mock serve function with content disposition logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_cid_content = Mock()
        self.mock_cid_content.file_data = b"test content"
        self.mock_cid_content.created_at = datetime.now(timezone.utc)

    def test_no_content_disposition_for_cid_only(self):
        """Test that CID-only paths don't get content disposition"""
        path = "/bafybeihelloworld123456789012345678901234567890123456"
        result = mock_serve_cid_content_with_disposition(self.mock_cid_content, path)

        self.assertNotIn("Content-Disposition", result.headers)

    def test_no_content_disposition_for_cid_with_extension(self):
        """Test that CID.ext paths don't get content disposition"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.txt"
        result = mock_serve_cid_content_with_disposition(self.mock_cid_content, path)

        self.assertNotIn("Content-Disposition", result.headers)

    def test_content_disposition_for_cid_with_filename(self):
        """Test that CID.filename.ext paths get content disposition"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.document.txt"
        result = mock_serve_cid_content_with_disposition(self.mock_cid_content, path)

        self.assertIn("Content-Disposition", result.headers)
        self.assertEqual(
            result.headers["Content-Disposition"], 'attachment; filename="document.txt"'
        )


if __name__ == "__main__":
    unittest.main()
