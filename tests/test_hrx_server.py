"""Unit tests for HRX server."""

import os
import unittest

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

# pylint: disable=wrong-import-position
from app import app, db
from identity import ensure_default_resources
from models import Server


class TestHRXServer(unittest.TestCase):
    """Test the HRX server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        ensure_default_resources()
        self.client = app.test_client()

        # Read the HRX server definition
        with open(
            "reference/templates/servers/definitions/hrx.py", "r", encoding="utf-8"
        ) as f:
            hrx_definition = f.read()

        # Create HRX server in database
        hrx_server = Server(name="hrx", definition=hrx_definition, enabled=True)
        db.session.add(hrx_server)
        db.session.commit()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_hrx_server_without_archive_raises_error(self):
        """Test that calling HRX server without archive raises an error."""
        response = self.client.get("/hrx")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"HRX archive is required", response.data)

    def test_hrx_server_with_empty_archive_raises_error(self):
        """Test that empty archive raises an error."""
        response = self.client.get("/hrx?archive=")
        self.assertEqual(response.status_code, 500)

    def test_hrx_server_lists_files_when_no_path(self):
        """Test that server lists files when no path is provided."""
        hrx_archive = "<===> file1.txt\ncontent1\n\n<===> file2.txt\ncontent2\n"
        response = self.client.post("/hrx", data={"archive": hrx_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file1.txt", response.data)
        self.assertIn(b"file2.txt", response.data)

    def test_hrx_server_returns_file_content(self):
        """Test that server returns file content when path is provided."""
        hrx_archive = "<===> test.txt\nHello World\nThis is a test\n"
        response = self.client.post(
            "/hrx", data={"archive": hrx_archive, "path": "test.txt"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "text/plain; charset=utf-8")
        self.assertIn(b"Hello World", response.data)
        self.assertIn(b"This is a test", response.data)

    def test_hrx_server_file_not_found(self):
        """Test that server raises error when file not found."""
        hrx_archive = "<===> exists.txt\ncontent\n"
        response = self.client.post(
            "/hrx", data={"archive": hrx_archive, "path": "notfound.txt"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Path not found", response.data)
        self.assertIn(b"notfound.txt", response.data)
        self.assertIn(b"exists.txt", response.data)

    def test_hrx_server_with_post_request(self):
        """Test HRX server with POST request containing archive in body."""
        hrx_archive = "<===> data.txt\nPosted content\n"
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "data.txt"},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Posted content", response.data)

    def test_hrx_server_with_multiple_files(self):
        """Test HRX server with multiple files."""
        hrx_archive = "<===> file1.txt\nContent 1\n\n<===> file2.txt\nContent 2\n\n<===> file3.txt\nContent 3\n"
        # List all files
        response = self.client.post("/hrx", data={"archive": hrx_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file1.txt", response.data)
        self.assertIn(b"file2.txt", response.data)
        self.assertIn(b"file3.txt", response.data)

        # Get specific file
        response = self.client.post(
            "/hrx", data={"archive": hrx_archive, "path": "file2.txt"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Content 2", response.data)
        self.assertNotIn(b"Content 1", response.data)
        self.assertNotIn(b"Content 3", response.data)

    def test_hrx_server_with_nested_paths(self):
        """Test HRX server with nested file paths."""
        hrx_archive = "<===> dir/subdir/nested.txt\nNested content\n"
        response = self.client.post("/hrx", data={"archive": hrx_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Root listing shows top-level directory
        self.assertIn(b"dir/", response.data)

        response = self.client.post(
            "/hrx", data={"archive": hrx_archive, "path": "dir/subdir/nested.txt"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nested content", response.data)

    def test_hrx_server_empty_archive_shows_message(self):
        """Test that empty archive (after boundary) shows appropriate message."""
        # Create an archive with a boundary but no actual files
        hrx_archive = "<===> "
        response = self.client.post("/hrx", data={"archive": hrx_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.strip(), b"")

    def test_hrx_server_invalid_hrx_format(self):
        """Test that invalid HRX format raises appropriate error."""
        invalid_archive = "This is not valid HRX format"
        response = self.client.post("/hrx", data={"archive": invalid_archive})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Invalid HRX archive", response.data)


if __name__ == "__main__":
    unittest.main()
