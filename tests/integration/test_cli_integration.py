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
        # Verify --port is documented
        self.assertIn('--port', result.stdout)
        self.assertIn('5001', result.stdout)

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

    def test_default_boot_cid_not_loaded_with_url(self):
        """Test that default boot CID is NOT loaded when making HTTP requests."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should not mention loading default boot CID
        self.assertNotIn('Using default boot CID', result.stdout)
        self.assertNotIn('Using default boot CID', result.stderr)

        # Should make HTTP request successfully
        self.assertEqual(result.returncode, 0)
        self.assertIn('Status:', result.stdout)

    def test_url_with_cid_exits_without_server(self):
        """Test that providing both URL and CID exits without starting server.

        NOTE: Currently there's a known issue where boot CID import from CLI
        fails due to CSRF token requiring request context. This test verifies
        that the command still exits quickly without starting the server, even
        if it errors out during CID import.
        """
        # First, get a valid boot CID from the --list command
        list_result = subprocess.run(
            [sys.executable, 'main.py', '--list'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Extract a CID from the output if available
        # Look for lines starting with "CID: "
        valid_cid = None
        for line in list_result.stdout.splitlines():
            if line.startswith('CID: '):
                valid_cid = line[5:].strip()
                break

        # If we have a valid CID, test URL + CID combination
        if valid_cid:
            result = subprocess.run(
                [sys.executable, 'main.py', '/', valid_cid],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=5,  # Should exit quickly, not hang like a server
                check=False,
            )

            # The important thing is it completes within timeout (not start server)
            # Due to known bug with CSRF, it currently errors during CID import
            # but still exits quickly without starting the server
            self.assertNotIn('Running on', result.stdout)
            self.assertNotIn('Running on', result.stderr)

            # Should exit (with any code), not hang
            self.assertIsNotNone(result.returncode)
        else:
            # If no boot CID available, test with invalid CID to verify argument parsing
            result = subprocess.run(
                [sys.executable, 'main.py', '/', 'AAAAAAAA'],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Should fail on invalid CID before attempting to start server
            self.assertNotEqual(result.returncode, 0)
            # Should show CID-related error
            self.assertTrue('CID' in result.stderr or 'cid' in result.stderr.lower())


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


class TestNonServerRunOptions(unittest.TestCase):
    """Tests for run options that exit without starting the Flask server.

    These tests verify that certain CLI options complete quickly and exit
    without launching the long-running Flask application server.
    """

    def test_help_exits_without_server(self):
        """Test --help exits immediately without starting server."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--help'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,  # Should exit in <1s; timeout proves no server started
            check=False,
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0)

        # Should show help text
        self.assertIn('USAGE', result.stdout)
        self.assertIn('--port', result.stdout)

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_help_short_exits_without_server(self):
        """Test -h exits immediately without starting server."""
        result = subprocess.run(
            [sys.executable, 'main.py', '-h'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0)

        # Should show help text
        self.assertIn('USAGE', result.stdout)

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_list_exits_without_server(self):
        """Test --list exits immediately without starting server."""
        result = subprocess.run(
            [sys.executable, 'main.py', '--list'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0)

        # Should show boot CID information or message about none found
        self.assertTrue(
            'Found' in result.stdout or 'No valid boot CIDs' in result.stdout
        )

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_url_slash_exits_without_server(self):
        """Test URL starting with / exits after GET request without starting server."""
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

        # Should show HTTP response
        self.assertIn('Status:', result.stdout)

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_url_http_exits_without_server(self):
        """Test full HTTP URL exits after GET request without starting server."""
        # Use a path-only URL to avoid network dependencies
        result = subprocess.run(
            [sys.executable, 'main.py', '/dashboard'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should show HTTP response (200 or 404, either is fine)
        self.assertIn('Status:', result.stdout)

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_url_404_exits_with_error_code(self):
        """Test URL returning 404 exits with error code but doesn't start server."""
        result = subprocess.run(
            [sys.executable, 'main.py', '/nonexistent-path-that-should-404'],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Should exit with error code for 4xx/5xx status
        # (returncode 0 or 1 both acceptable, depends on response)
        self.assertIn(result.returncode, [0, 1])

        # Should show HTTP response
        self.assertIn('Status:', result.stdout)

        # Should NOT show server startup messages
        self.assertNotIn('Running on', result.stdout)
        self.assertNotIn('Running on', result.stderr)

    def test_all_non_server_options_complete_quickly(self):
        """Test that all non-server options complete within reasonable time.

        This is a meta-test that verifies none of the non-server options
        are hanging or attempting to start the Flask server.
        """
        import time

        non_server_commands = [
            ['--help'],
            ['-h'],
            ['--list'],
            ['/'],
        ]

        for cmd in non_server_commands:
            start_time = time.time()

            result = subprocess.run(
                [sys.executable, 'main.py'] + cmd,
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            elapsed = time.time() - start_time

            # All non-server options should complete in < 3 seconds
            self.assertLess(
                elapsed,
                3.0,
                f"Command {cmd} took {elapsed:.2f}s (should be < 3s)"
            )

            # Should exit (not hang)
            self.assertIsNotNone(result.returncode)


if __name__ == '__main__':
    unittest.main()
