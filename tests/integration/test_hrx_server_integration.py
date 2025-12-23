"""Integration tests for HRX server."""

import os
import unittest

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

# pylint: disable=wrong-import-position
from app import app, db
from identity import ensure_default_resources
from models import Server


class TestHRXServerIntegration(unittest.TestCase):
    """Integration tests for HRX server."""

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
            "reference_templates/servers/definitions/hrx.py", "r", encoding="utf-8"
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

    def test_hrx_server_end_to_end_workflow(self):
        """Test complete HRX server workflow from archive to file retrieval."""
        # Create a sample HRX archive
        hrx_archive = """<===> readme.txt
This is a README file

<===> config.json
{
  "name": "test",
  "version": "1.0"
}

<===> src/main.py
def main():
    print("Hello World")
"""

        # Step 1: List all files in the archive
        response = self.client.post(
            "/hrx", data={"archive": hrx_archive}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"HRX Archive Contents", response.data)
        self.assertIn(b"readme.txt", response.data)
        self.assertIn(b"config.json", response.data)
        self.assertIn(b"src/main.py", response.data)
        self.assertIn(b"3 total", response.data)

        # Step 2: Retrieve the readme file
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "readme.txt"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "text/plain; charset=utf-8")
        self.assertIn(b"This is a README file", response.data)

        # Step 3: Retrieve the JSON config
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "config.json"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"name": "test"', response.data)
        self.assertIn(b'"version": "1.0"', response.data)

        # Step 4: Retrieve nested file
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "src/main.py"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"def main():", response.data)
        self.assertIn(b'print("Hello World")', response.data)

    def test_hrx_server_error_handling(self):
        """Test HRX server error handling."""
        hrx_archive = "<===> valid.txt\nContent\n"

        # Test missing file
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "nonexistent.txt"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"File not found: nonexistent.txt", response.data)
        self.assertIn(b"valid.txt", response.data)  # Should show available files

        # Test missing archive
        response = self.client.post(
            "/hrx", data={"path": "some.txt"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"HRX archive is required", response.data)

    def test_hrx_server_with_real_world_example(self):
        """Test HRX server with a real-world-like test case archive."""
        # This mimics how HRX is commonly used in test suites
        hrx_archive = """<===> input.scss
$primary-color: #333;

body {
  color: $primary-color;
}

<===> expected.css
body {
  color: #333;
}

<===> test-description.md
# Test Case: Variable Substitution

This test verifies that SCSS variables are correctly
substituted in the compiled output.
"""

        # List files
        response = self.client.post(
            "/hrx", data={"archive": hrx_archive}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"input.scss", response.data)
        self.assertIn(b"expected.css", response.data)
        self.assertIn(b"test-description.md", response.data)

        # Retrieve input
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "input.scss"},
            follow_redirects=True,
        )
        self.assertIn(b"$primary-color: #333;", response.data)

        # Retrieve expected output
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "expected.css"},
            follow_redirects=True,
        )
        self.assertIn(b"color: #333;", response.data)

        # Retrieve description
        response = self.client.post(
            "/hrx",
            data={"archive": hrx_archive, "path": "test-description.md"},
            follow_redirects=True,
        )
        self.assertIn(b"# Test Case: Variable Substitution", response.data)
        self.assertIn(b"SCSS variables", response.data)


if __name__ == "__main__":
    unittest.main()
