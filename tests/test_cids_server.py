"""Unit tests for CIDS server."""

import os
import unittest

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

# pylint: disable=wrong-import-position
from app import app, db
from identity import ensure_default_resources
from models import Server


class TestCIDSServer(unittest.TestCase):
    """Test the CIDS server functionality."""

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

        # Read the CIDS server definition
        with open(
            "reference/templates/servers/definitions/cids.py", "r", encoding="utf-8"
        ) as f:
            cids_definition = f.read()

        # Create CIDS server in database
        cids_server = Server(name="cids", definition=cids_definition, enabled=True)
        db.session.add(cids_server)
        db.session.commit()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_cids_server_without_archive_raises_error(self):
        """Test that calling CIDS server without archive raises an error."""
        response = self.client.get("/cids")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"CIDS archive is required", response.data)

    def test_cids_server_with_empty_archive_raises_error(self):
        """Test that empty archive raises an error."""
        response = self.client.get("/cids?archive=")
        self.assertEqual(response.status_code, 500)

    def test_cids_server_lists_files_when_no_path(self):
        """Test that server lists files when no path is provided."""
        cids_archive = "file1.txt CID_FILE1\nfile2.txt CID_FILE2\n"
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file1.txt", response.data)
        self.assertIn(b"file2.txt", response.data)

    def test_cids_server_invalid_format_raises_error(self):
        """Test that invalid CIDS format raises an error."""
        # Line with only one token (missing CID)
        invalid_archive = "file_without_cid"
        response = self.client.post("/cids", data={"archive": invalid_archive}, follow_redirects=True)
        # Should return an error status and message
        self.assertIn(response.status_code, [400, 500])
        self.assertIn(b"Invalid", response.data)

    def test_cids_server_duplicate_paths_raises_error(self):
        """Test that duplicate paths raise an error."""
        duplicate_archive = "file.txt CID1\nfile.txt CID2\n"
        response = self.client.post("/cids", data={"archive": duplicate_archive})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Duplicate path", response.data)

    def test_cids_server_path_not_found(self):
        """Test that server raises error when path not found."""
        cids_archive = "exists.txt CID_EXISTS\n"
        response = self.client.post(
            "/cids", data={"archive": cids_archive, "path": "notfound.txt"}, follow_redirects=True
        )
        # Should return an error (either 404 or 500 depending on error handling)
        self.assertIn(response.status_code, [404, 500])
        self.assertIn(b"notfound.txt", response.data)
        # Should mention available files
        self.assertIn(b"exists.txt", response.data)

    def test_cids_server_with_post_request(self):
        """Test CIDS server with POST request containing archive in body."""
        cids_archive = "data.txt CID_DATA\n"
        response = self.client.post(
            "/cids",
            data={"archive": cids_archive, "path": "data.txt"},
            follow_redirects=True
        )
        # Since CID_DATA doesn't exist, this should return 404
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"CID not found", response.data)

    def test_cids_server_with_multiple_files(self):
        """Test CIDS server with multiple files."""
        cids_archive = "file1.txt CID1\nfile2.txt CID2\nfile3.txt CID3\n"
        # List all files
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file1.txt", response.data)
        self.assertIn(b"file2.txt", response.data)
        self.assertIn(b"file3.txt", response.data)

    def test_cids_server_with_nested_paths(self):
        """Test CIDS server with nested file paths."""
        cids_archive = "dir/subdir/nested.txt CID_NESTED\n"
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Root listing shows top-level directory
        self.assertIn(b"dir/", response.data)

    def test_cids_server_empty_archive_shows_error(self):
        """Test that empty archive shows appropriate error."""
        empty_archive = ""
        response = self.client.post("/cids", data={"archive": empty_archive})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Invalid CIDS archive", response.data)

    def test_cids_server_whitespace_only_archive_shows_error(self):
        """Test that whitespace-only archive shows appropriate error."""
        whitespace_archive = "   \n  \n  "
        response = self.client.post("/cids", data={"archive": whitespace_archive})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Invalid CIDS archive", response.data)

    def test_cids_server_skips_empty_lines(self):
        """Test that empty lines are skipped."""
        cids_archive = "file1.txt CID1\n\nfile2.txt CID2\n  \nfile3.txt CID3\n"
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file1.txt", response.data)
        self.assertIn(b"file2.txt", response.data)
        self.assertIn(b"file3.txt", response.data)

    def test_cids_server_cid_with_extension(self):
        """Test that CID can have extensions for MIME types."""
        cids_archive = "file.html CID123.html\nfile.txt CID456.txt\n"
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file.html", response.data)
        self.assertIn(b"file.txt", response.data)

    def test_cids_server_directory_listing(self):
        """Test directory listing functionality."""
        cids_archive = "docs/readme.md CID1\ndocs/api.md CID2\nsrc/main.py CID3\n"
        # List root
        response = self.client.post("/cids", data={"archive": cids_archive}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"docs/", response.data)
        self.assertIn(b"src/", response.data)

        # List docs directory
        response = self.client.post(
            "/cids", data={"archive": cids_archive, "path": "docs"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"readme.md", response.data)
        self.assertIn(b"api.md", response.data)
        self.assertNotIn(b"main.py", response.data)


if __name__ == "__main__":
    unittest.main()
