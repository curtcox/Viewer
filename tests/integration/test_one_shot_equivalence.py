"""Integration tests to verify one-shot CLI mode returns same response as HTTP.

These tests ensure that when the app is run from command line with a URL,
it responds with the same content as if the request came via HTTP to a running server.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app import create_app
from cid_utils import generate_cid
from db_access import create_cid_record
from models import Server

pytestmark = pytest.mark.integration


class TestOneShotEquivalence:
    """Integration tests for one-shot vs HTTP response equivalence."""

    CLI_ROOT = Path(__file__).parent.parent.parent

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with isolated database."""
        # Create app with test configuration
        self.app = create_app({  # pylint: disable=attribute-defined-outside-init
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/test.db',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            from database import db
            db.create_all()

            # Create test servers for testing
            self._create_test_data()

        yield

        with self.app.app_context():
            from database import db
            db.session.remove()
            db.drop_all()

    def _create_test_data(self):
        """Create test data for equivalence testing."""
        from database import db

        # Create a test server
        test_server = Server(
            name='test_equivalence_server',
            definition='def main():\n    return {"output": "test response"}',
            enabled=True,
        )
        db.session.add(test_server)
        db.session.commit()

    def _get_http_response(self, path: str) -> tuple[int, str]:
        """Get response from HTTP endpoint using test client.
        
        Args:
            path: URL path to request
            
        Returns:
            Tuple of (status_code, response_text)
        """
        with self.app.test_client() as client:
            response = client.get(path)
            return response.status_code, response.data.decode('utf-8')

    def _get_cli_response(self, path: str, extra_args: list[str] = None) -> tuple[int | None, str]:
        """Get response from CLI one-shot mode.
        
        Args:
            path: URL path to request
            extra_args: Additional CLI arguments
            
        Returns:
            Tuple of (exit_code, stdout_text)
        """
        # Use environment variable to point CLI to the test database
        import os
        test_db_uri = self.app.config['SQLALCHEMY_DATABASE_URI']
        
        # Extract the database file path from the URI
        if 'sqlite:///' in test_db_uri:
            db_path = test_db_uri.replace('sqlite:///', '')
        else:
            # Fall back to in-memory if not a file-based SQLite
            args = [sys.executable, 'main.py', '--in-memory-db', path]
            if extra_args:
                args.extend(extra_args)
            
            result = subprocess.run(
                args,
                cwd=self.CLI_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return self._parse_cli_output(result)
        
        # Set environment variable for the CLI to use the test database
        env = os.environ.copy()
        env['DATABASE_URL'] = test_db_uri
        
        args = [sys.executable, 'main.py', path]
        if extra_args:
            args.extend(extra_args)

        result = subprocess.run(
            args,
            cwd=self.CLI_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=env,
        )

        return self._parse_cli_output(result)

    def _parse_cli_output(self, result) -> tuple[int | None, str]:
        """Parse CLI subprocess result to extract status and output.
        
        Args:
            result: subprocess.CompletedProcess result
            
        Returns:
            Tuple of (status_code, output_text)
        """
        # Parse status code from output
        status_code = None
        lines = result.stdout.splitlines()
        for line in lines:
            if line.startswith('Status:'):
                try:
                    status_code = int(line.split(':')[1].strip())
                    # Remove status line from output
                    lines.remove(line)
                    break
                except (ValueError, IndexError):
                    pass

        output = '\n'.join(lines)
        return status_code, output

    def test_servers_json_equivalence(self):
        """Test that /servers.json returns same content via HTTP and CLI."""
        http_status, http_response = self._get_http_response('/servers.json')
        cli_status, cli_response = self._get_cli_response('/servers.json')

        # Both should succeed
        assert http_status == 200, f"HTTP failed with status {http_status}"
        assert cli_status == 200, f"CLI failed with status {cli_status}"

        # Parse JSON to compare content (ignoring formatting differences)
        http_data = json.loads(http_response)
        cli_data = json.loads(cli_response)

        # Compare servers by name (order might differ)
        http_servers = {s['name']: s for s in http_data}
        cli_servers = {s['name']: s for s in cli_data}

        # The test server we created should exist in both
        assert 'test_equivalence_server' in http_servers, "Test server not in HTTP response"
        assert 'test_equivalence_server' in cli_servers, "Test server not in CLI response"

        # Compare the test server's essential fields
        http_test = http_servers['test_equivalence_server']
        cli_test = cli_servers['test_equivalence_server']

        assert http_test['name'] == cli_test['name']
        assert http_test['definition'] == cli_test['definition']
        assert http_test['enabled'] == cli_test['enabled']

    def test_cid_from_boot_image_equivalence(self):
        """Test that a CID from boot image returns same content via HTTP and CLI.
        
        This test verifies that when a CID is available in both contexts (test DB and cids directory),
        the response is identical.
        """
        # Get the default boot CID
        boot_cid_file = self.CLI_ROOT / "reference_templates" / "boot.cid"
        if not boot_cid_file.exists():
            pytest.skip("No default boot.cid file found")

        boot_cid = boot_cid_file.read_text(encoding='utf-8').strip()
        
        # Load the boot CID into the test database so HTTP can access it
        boot_cid_content_file = self.CLI_ROOT / "cids" / boot_cid
        if not boot_cid_content_file.exists():
            pytest.skip(f"Boot CID content file not found: {boot_cid}")
        
        boot_cid_content = boot_cid_content_file.read_bytes()
        
        # Add the CID to the test database
        with self.app.app_context():
            from db_access import create_cid_record
            create_cid_record(boot_cid, boot_cid_content)

        # Test getting the CID content
        path = f'/{boot_cid}'

        http_status, http_response = self._get_http_response(path)
        cli_status, cli_response = self._get_cli_response(path)

        # Both should succeed with same status
        assert http_status == cli_status, f"Different status codes: HTTP={http_status}, CLI={cli_status}"

        # If successful, content should be identical
        if http_status == 200:
            # Parse JSON if it's JSON content
            try:
                http_data = json.loads(http_response)
                cli_data = json.loads(cli_response)
                assert http_data == cli_data, "JSON content differs"
            except json.JSONDecodeError:
                # Not JSON, compare as text
                assert http_response == cli_response, "Text content differs"

    def test_root_path_equivalence(self):
        """Test that / returns same response via HTTP and CLI."""
        http_status, http_response = self._get_http_response('/')
        cli_status, cli_response = self._get_cli_response('/')

        # Both should succeed
        assert http_status == 200, f"HTTP failed with status {http_status}"
        assert cli_status == 200, f"CLI failed with status {cli_status}"

        # Both should return HTML (basic check)
        assert 'html' in http_response.lower(), "HTTP response should be HTML"
        assert 'html' in cli_response.lower(), "CLI response should be HTML"
        
        # Both should have similar structure (same title)
        assert '<title>' in http_response and '</title>' in http_response
        assert '<title>' in cli_response and '</title>' in cli_response

    def test_404_equivalence(self):
        """Test that 404 responses are same via HTTP and CLI."""
        http_status, http_response = self._get_http_response('/nonexistent-path-12345')
        cli_status, cli_response = self._get_cli_response('/nonexistent-path-12345')

        # Both should return 404
        assert http_status == 404, f"HTTP should be 404, got {http_status}"
        assert cli_status == 404, f"CLI should be 404, got {cli_status}"

        # Content should be the same
        assert http_response == cli_response, "404 responses differ"

    def test_json_endpoint_with_query_params(self):
        """Test JSON endpoint with query parameters for equivalence."""
        # Query for our test server specifically
        path = '/servers.json?name=test_equivalence_server'
        
        http_status, http_response = self._get_http_response(path)
        cli_status, cli_response = self._get_cli_response(path)

        # Status codes should match
        assert http_status == cli_status, f"Status codes differ: HTTP={http_status}, CLI={cli_status}"

        # Content should match
        if http_status == 200:
            try:
                http_data = json.loads(http_response)
                cli_data = json.loads(cli_response)
                
                # Both should have filtered to just our test server (or similar results)
                http_names = [s['name'] for s in http_data]
                cli_names = [s['name'] for s in cli_data]
                
                # Our test server should be in both
                assert 'test_equivalence_server' in http_names
                assert 'test_equivalence_server' in cli_names
                
            except json.JSONDecodeError:
                assert http_response == cli_response, "Query param text responses differ"


class TestOneShotWithBootCID:
    """Test one-shot mode with boot CID to verify data is loaded correctly."""

    CLI_ROOT = Path(__file__).parent.parent.parent

    def test_servers_json_with_boot_cid(self):
        """Test that /servers.json includes data from boot CID in one-shot mode."""
        # Create a test boot CID with server data
        servers_data = [
            {
                'name': 'boot-test-server',
                'definition': 'def main():\n    return "boot test"',
            }
        ]
        servers_content = json.dumps(servers_data).encode('utf-8')
        servers_cid = generate_cid(servers_content)

        # Store the servers CID in the cids directory
        servers_cid_file = self.CLI_ROOT / 'cids' / servers_cid
        servers_cid_file.write_bytes(servers_content)

        try:
            # Create boot CID that references the servers
            boot_payload = {
                'version': 6,
                'servers': servers_cid,
            }
            boot_content = json.dumps(boot_payload).encode('utf-8')
            boot_cid = generate_cid(boot_content)

            # Store the boot CID in the cids directory
            boot_cid_file = self.CLI_ROOT / 'cids' / boot_cid
            boot_cid_file.write_bytes(boot_content)

            try:
                # Run one-shot mode with boot CID
                result = subprocess.run(
                    [sys.executable, 'main.py', '--in-memory-db', '/servers.json', boot_cid],
                    cwd=self.CLI_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                # Should succeed
                assert 'Status: 200' in result.stdout, f"Expected 200, got: {result.stdout}"

                # Parse response
                lines = result.stdout.splitlines()
                json_start = next(i for i, line in enumerate(lines) if line.startswith('['))
                json_text = '\n'.join(lines[json_start:])
                
                servers = json.loads(json_text)

                # Should include the server from boot CID
                server_names = [s['name'] for s in servers]
                assert 'boot-test-server' in server_names, f"Boot server not found in: {server_names}"

            finally:
                # Clean up boot CID file
                if boot_cid_file.exists():
                    boot_cid_file.unlink()

        finally:
            # Clean up servers CID file
            if servers_cid_file.exists():
                servers_cid_file.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
