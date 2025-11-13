"""Integration tests for CLI main.py entry point.

Note: These tests use subprocess to test the CLI directly,
so they use the actual application database, not an in-memory database.
Tests should not depend on specific database state.
"""

import subprocess
import sys
import unittest
from pathlib import Path

from cid_utils import generate_cid


class TestCliIntegration(unittest.TestCase):
    """Integration tests for CLI functionality.

    Note: These tests run the CLI via subprocess, so they use the
    application's default database configuration, not an in-memory test database.
    """

    def test_help_flag(self):
        """Test --help flag shows help message."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--help'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('USAGE', result.stdout)
        self.assertIn('OPTIONS', result.stdout)
        self.assertIn('EXAMPLES', result.stdout)

    def test_list_flag(self):
        """Test --list flag lists boot CIDs."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--list'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should exit with 0
        self.assertEqual(result.returncode, 0)

        # Should contain information about CIDs
        # (may have CIDs from cids directory)
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
            check=False,
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
            check=False,
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
            check=False,
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
            check=False,
        )

        # Should exit with 0 for successful request
        # (might be 1 if 404, but should not crash)
        self.assertIn(result.returncode, [0, 1])

        # Should show status and response
        self.assertIn('Status:', result.stdout)

    def test_url_only_http(self):
        """Test providing only a full HTTP URL using path-only to avoid external dependency."""
        # Use path-only URL to avoid external network dependency
        result = subprocess.run(
            [sys.executable, 'main.py', '/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
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
            check=False,
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
            check=False,
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
            check=False,
        )

        # Will fail because AAAAAAAA is empty CID, but should recognize the flag
        # and not complain about unknown argument
        self.assertNotIn('unrecognized arguments', result.stderr)


class TestCliArgumentParsing(unittest.TestCase):
    """Tests for CLI argument parsing logic."""

    def test_help_long_form(self):
        """Test --help works."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--help'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('USAGE', result.stdout)

    def test_help_short_form(self):
        """Test -h works."""
        result = subprocess.run(
            [sys.executable, 'main.py', '-h'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
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
            check=False,
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
            check=False,
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
            check=False,
        )

        # Should make HTTP request
        self.assertIn('Status:', result.stdout)

    def test_https_is_url(self):
        """Test string starting with https:// is treated as URL."""
        # Use localhost to avoid external network dependency
        result = subprocess.run(
            [sys.executable, 'main.py', 'https://localhost:9999/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should fail to connect (no server running) but be treated as URL
        # (not CID validation error)
        self.assertNotIn('Invalid CID', result.stderr)
        # Should show it attempted to make an HTTP request
        self.assertTrue('Error' in result.stderr or 'Status:' in result.stdout)


if __name__ == '__main__':
    unittest.main()
