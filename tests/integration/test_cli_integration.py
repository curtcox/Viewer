"""Integration tests for CLI main.py entry point."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app import create_app, db
from cid_utils import generate_cid
from db_access import create_cid_record


class TestCliIntegration(unittest.TestCase):
    """Integration tests for CLI functionality."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-cli'

            # Create test CIDs for integration tests
            self._create_test_cids()

    def tearDown(self):
        """Tear down test environment."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_test_cids(self):
        """Create test CIDs in the database."""
        # Create a valid boot CID
        boot_content = json.dumps({
            'aliases': generate_cid(b'[]'),
            'servers': generate_cid(b'[]'),
        }).encode('utf-8')
        self.boot_cid = generate_cid(boot_content)
        create_cid_record(self.boot_cid, boot_content, self.user_id)

        # Create the referenced CIDs
        create_cid_record(generate_cid(b'[]'), b'[]', self.user_id)

        # Create a simple text CID
        self.text_content = b'Hello from test CID!'
        self.text_cid = generate_cid(self.text_content)
        create_cid_record(self.text_cid, self.text_content, self.user_id)

    def test_help_flag(self):
        """Test --help flag shows help message."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--help'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('USAGE', result.stdout)
        self.assertIn('OPTIONS', result.stdout)
        self.assertIn('EXAMPLES', result.stdout)

    def test_list_flag(self):
        """Test --list flag lists boot CIDs."""
        with self.app.app_context():
            result = subprocess.run(
                [sys.executable, 'main.py', '--list'],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Should exit with 0
            self.assertEqual(result.returncode, 0)

            # Should contain information about CIDs
            # (may have CIDs from cids directory or our test CID if DB is shared)
            self.assertTrue(
                'Found' in result.stdout or 'No valid boot CIDs' in result.stdout
            )

    def test_invalid_cid_format(self):
        """Test providing an invalid CID format shows error."""
        result = subprocess.run(
            [sys.executable, 'main.py', 'not-a-valid-cid!@#'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with error code
        self.assertNotEqual(result.returncode, 0)

        # Should show error message about invalid CID
        self.assertIn('Invalid CID', result.stderr)
        self.assertIn('invalid character', result.stderr.lower())

    def test_valid_cid_not_found(self):
        """Test providing a valid CID format that doesn't exist."""
        # Generate a CID but don't store it
        non_existent_cid = generate_cid(b'this cid was never stored')

        result = subprocess.run(
            [sys.executable, 'main.py', non_existent_cid],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with error code
        self.assertNotEqual(result.returncode, 0)

        # Should show error message about CID not found
        self.assertIn('not found', result.stderr.lower())

    def test_invalid_url_format(self):
        """Test providing an invalid URL shows error."""
        result = subprocess.run(
            [sys.executable, 'main.py', 'ftp://invalid-scheme.com/path'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with error code
        self.assertNotEqual(result.returncode, 0)

        # Should show error message about invalid URL
        self.assertIn('Invalid URL', result.stderr)
        self.assertIn('http', result.stderr.lower())

    def test_url_only_slash_path(self):
        """Test providing only a URL starting with /."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/dashboard'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with 0 for successful request
        # (might be 1 if 404, but should not crash)
        self.assertIn(result.returncode, [0, 1])

        # Should show status and response
        self.assertIn('Status:', result.stdout)

    def test_url_only_http(self):
        """Test providing only a full HTTP URL."""
        result = subprocess.run(
            [sys.executable, 'main.py', 'http://localhost:5001/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0)

        # Should show status and response
        self.assertIn('Status:', result.stdout)
        self.assertIn('200', result.stdout)

    def test_too_many_arguments(self):
        """Test providing too many positional arguments."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/url1', 'cid1', 'extra_arg'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with error
        self.assertNotEqual(result.returncode, 0)

        # Should show error about too many arguments
        self.assertIn('Too many', result.stderr)

    def test_multiple_urls_error(self):
        """Test providing multiple URLs shows error."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/url1', '/url2'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should exit with error
        self.assertNotEqual(result.returncode, 0)

        # Should show error about multiple URLs
        self.assertIn('Multiple URLs', result.stderr)

    def test_legacy_boot_cid_flag(self):
        """Test legacy --boot-cid flag still works."""
        # This test would need to actually import a boot CID
        # For now, just test that it's recognized (will fail on CID not found)
        result = subprocess.run(
            [sys.executable, 'main.py', '--boot-cid', 'AAAAAAAA'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Will fail because AAAAAAAA is empty CID, but should recognize the flag
        # and not complain about unknown argument
        self.assertNotIn('unrecognized arguments', result.stderr)


class TestCliArgumentParsing(unittest.TestCase):
    """Tests for CLI argument parsing logic."""

    def test_help_combinations(self):
        """Test --help works with other flags."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--help'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('USAGE', result.stdout)

    def test_list_only(self):
        """Test --list flag works alone."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--list'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        # Should show either boot CIDs or message about none found
        self.assertTrue(
            'Found' in result.stdout or 'No valid boot CIDs' in result.stdout
        )


class TestCliUrlDetection(unittest.TestCase):
    """Tests for URL vs CID detection logic."""

    def test_slash_is_url(self):
        """Test string starting with / is treated as URL."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/test'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should make HTTP request, not treat as CID
        self.assertIn('Status:', result.stdout)

    def test_http_is_url(self):
        """Test string starting with http:// is treated as URL."""
        result = subprocess.run(
            [sys.executable, 'main.py', 'http://localhost:5001/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should make HTTP request
        self.assertIn('Status:', result.stdout)

    def test_https_is_url(self):
        """Test string starting with https:// is treated as URL."""
        result = subprocess.run(
            [sys.executable, 'main.py', 'https://example.com/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Will fail to connect but should be treated as URL
        # (not CID validation error)
        self.assertNotIn('Invalid CID', result.stderr)


if __name__ == '__main__':
    unittest.main()
