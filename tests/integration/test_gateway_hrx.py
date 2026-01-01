"""Integration tests for HRX gateway functionality using one-shot mode.

These tests verify that /gateway/hrx/{cid}/{path} requests can read
the properly linked contents from an HRX CID archive.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from boot_cid_importer import import_boot_cid
from app import create_app
from cid_utils import generate_cid
from db_access import create_cid_record

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires running HTTP server for gateway proxy - oneshot mode cannot proxy")
class TestGatewayHRXOneShot:
    """Integration tests for HRX gateway using one-shot CLI mode.

    Note: These tests are skipped because the gateway's proxy mechanism requires
    a running HTTP server to forward requests to /servers/{name}/{path}. The
    oneshot CLI mode runs in a subprocess without a server.
    """

    CLI_ROOT = Path(__file__).parent.parent.parent

    def _create_hrx_archive(self, files: dict) -> bytes:
        """Create an HRX archive from a dict of {filename: content}.

        Args:
            files: Dict mapping filenames to their contents

        Returns:
            HRX archive as bytes
        """
        parts = []
        for filename, content in files.items():
            parts.append(f"<===> {filename}\n{content}\n")
        return "\n".join(parts).encode("utf-8")

    def _store_cid(self, content: bytes) -> str:
        """Store content as CID in the cids directory.

        Args:
            content: Content bytes to store

        Returns:
            CID of the stored content
        """
        cid = generate_cid(content)
        cid_file = self.CLI_ROOT / "cids" / cid
        cid_file.write_bytes(content)
        return cid

    def _run_oneshot(self, path: str, boot_cid: str) -> tuple[int, str]:
        """Run one-shot CLI request.

        Args:
            path: URL path to request
            boot_cid: Boot CID to use

        Returns:
            Tuple of (status_code, response_text)
        """
        env = os.environ.copy()
        env.pop("TESTING", None)

        result = subprocess.run(
            [
                sys.executable,
                "main.py",
                "--in-memory-db",
                path,
                boot_cid,
            ],
            cwd=self.CLI_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )

        # Parse status code from output
        status_code = None
        lines = result.stdout.splitlines()
        output_lines = []

        for line in lines:
            if line.startswith("Status:"):
                try:
                    status_code = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            else:
                output_lines.append(line)

        return status_code, "\n".join(output_lines)

    def _get_default_boot_cid(self) -> str:
        """Get the default boot CID from reference_templates."""
        boot_cid_file = self.CLI_ROOT / "reference_templates" / "default.boot.cid"
        if not boot_cid_file.exists():
            pytest.skip("No default.boot.cid file found")
        return boot_cid_file.read_text(encoding="utf-8").strip()

    def test_gateway_hrx_returns_file_from_archive(self):
        """Test that /gateway/hrx/{cid}/{path} returns file content from HRX archive."""
        # Create an HRX archive with test files
        hrx_content = self._create_hrx_archive({
            "readme.txt": "Hello from HRX archive!",
            "data.json": '{"message": "test data"}',
        })

        # Store the archive as a CID
        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            # Request a file from the archive
            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/readme.txt",
                boot_cid,
            )

            # Should succeed
            assert status == 200, f"Expected 200, got {status}. Response: {response}"

            # Response should contain the file content
            assert "Hello from HRX archive!" in response, (
                f"Expected file content in response: {response}"
            )

        finally:
            # Clean up
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_returns_json_file(self):
        """Test that /gateway/hrx returns JSON file content correctly."""
        # Create an HRX archive with a JSON file
        hrx_content = self._create_hrx_archive({
            "config.json": '{"setting": "value", "count": 42}',
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/config.json",
                boot_cid,
            )

            assert status == 200, f"Expected 200, got {status}"
            # JSON content should be present
            assert "setting" in response
            assert "value" in response

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_lists_files_at_root(self):
        """Test that /gateway/hrx/{cid}/ lists archive contents."""
        # Create an HRX archive with multiple files
        hrx_content = self._create_hrx_archive({
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "subdir/file3.txt": "Content 3",
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            # Request the archive root
            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}",
                boot_cid,
            )

            assert status == 200, f"Expected 200, got {status}"
            # Should show file listing or archive contents
            assert "file1.txt" in response or "Archive" in response, (
                f"Expected file listing: {response}"
            )

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_file_not_found(self):
        """Test that /gateway/hrx returns error for non-existent file."""
        # Create an HRX archive with one file
        hrx_content = self._create_hrx_archive({
            "exists.txt": "This file exists",
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            # Request a file that doesn't exist
            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/nonexistent.txt",
                boot_cid,
            )

            # Should return an error page (200 with error content or 404)
            # The HRX gateway wraps errors in HTML
            assert status in (200, 404, 500), f"Unexpected status: {status}"
            assert (
                "not found" in response.lower()
                or "error" in response.lower()
                or "Error" in response
            ), f"Expected error message: {response}"

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_markdown_rendering(self):
        """Test that /gateway/hrx renders markdown files as HTML."""
        # Create an HRX archive with a markdown file
        hrx_content = self._create_hrx_archive({
            "README.md": "# Hello World\n\nThis is a **test** markdown file.",
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/README.md",
                boot_cid,
            )

            assert status == 200, f"Expected 200, got {status}"
            # Markdown should be rendered as HTML
            assert "html" in response.lower(), "Response should be HTML"
            # Title should be rendered
            assert "Hello World" in response

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_nested_path(self):
        """Test that /gateway/hrx handles nested file paths."""
        # Create an HRX archive with nested structure
        hrx_content = self._create_hrx_archive({
            "docs/api/reference.txt": "API Reference Documentation",
            "docs/index.html": "<html><body>Docs Index</body></html>",
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            # Request nested file
            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/docs/api/reference.txt",
                boot_cid,
            )

            assert status == 200, f"Expected 200, got {status}"
            assert "API Reference Documentation" in response

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()

    def test_gateway_hrx_html_file(self):
        """Test that /gateway/hrx returns HTML files with proper content type."""
        # Create an HRX archive with an HTML file
        html_content = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body><h1>Test Content</h1></body>
</html>"""
        hrx_content = self._create_hrx_archive({
            "index.html": html_content,
        })

        archive_cid = self._store_cid(hrx_content)

        try:
            boot_cid = self._get_default_boot_cid()

            status, response = self._run_oneshot(
                f"/gateway/hrx/{archive_cid}/index.html",
                boot_cid,
            )

            assert status == 200, f"Expected 200, got {status}"
            assert "Test Content" in response

        finally:
            cid_file = self.CLI_ROOT / "cids" / archive_cid
            if cid_file.exists():
                cid_file.unlink()


@pytest.mark.skip(reason="Requires running HTTP server for gateway proxy - Flask test client cannot intercept requests library calls")
class TestGatewayHRXWithHTTPClient:
    """Integration tests for HRX gateway using HTTP client with test database.

    Note: These tests are skipped because the gateway uses the `requests` library
    to make HTTP requests to /servers/{name}/{path}. Flask's test client only
    intercepts requests made through the test client itself, not HTTP requests
    made by application code using `requests`.

    To run these tests, you need a running server instance or mock the requests library.
    """

    @pytest.fixture
    def app_with_gateway(self, tmp_path):
        """Create app with gateway server and gateways variable."""
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
                "LOAD_CIDS_IN_TESTS": True,
            }
        )

        # Load default boot CID to get gateway server and gateways variable
        boot_cid_file = Path(__file__).parent.parent.parent / "reference_templates" / "default.boot.cid"
        if not boot_cid_file.exists():
            pytest.skip("No default.boot.cid file found")

        boot_cid = boot_cid_file.read_text(encoding="utf-8").strip()

        with app.app_context():
            success, error = import_boot_cid(app, boot_cid)
            if not success:
                pytest.skip(f"Failed to import boot CID: {error}")

        return app

    def _create_hrx_archive(self, files: dict) -> bytes:
        """Create an HRX archive from a dict of {filename: content}."""
        parts = []
        for filename, content in files.items():
            parts.append(f"<===> {filename}\n{content}\n")
        return "\n".join(parts).encode("utf-8")

    def test_gateway_hrx_http_returns_file(self, app_with_gateway):
        """Test HRX gateway via HTTP client."""
        # Create an HRX archive
        hrx_content = self._create_hrx_archive({
            "hello.txt": "Hello from HTTP test!",
        })

        with app_with_gateway.app_context():
            # Store the archive as a CID
            archive_cid = generate_cid(hrx_content)
            create_cid_record(archive_cid, hrx_content)

        with app_with_gateway.test_client() as client:
            response = client.get(f"/gateway/hrx/{archive_cid}/hello.txt")

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.data}"
            )
            assert b"Hello from HTTP test!" in response.data

    def test_gateway_hrx_http_archive_listing(self, app_with_gateway):
        """Test HRX gateway archive listing via HTTP."""
        hrx_content = self._create_hrx_archive({
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
        })

        with app_with_gateway.app_context():
            archive_cid = generate_cid(hrx_content)
            create_cid_record(archive_cid, hrx_content)

        with app_with_gateway.test_client() as client:
            response = client.get(f"/gateway/hrx/{archive_cid}")

            assert response.status_code == 200
            data = response.data.decode("utf-8")
            # Should list files or show archive contents
            assert "file1.txt" in data or "Archive" in data

    def test_gateway_hrx_http_relative_links(self, app_with_gateway):
        """Test that HRX gateway fixes relative links in HTML files."""
        html_content = '''<html>
<body>
<a href="other.html">Other Page</a>
<img src="images/logo.png">
</body>
</html>'''

        hrx_content = self._create_hrx_archive({
            "index.html": html_content,
            "other.html": "<html><body>Other</body></html>",
        })

        with app_with_gateway.app_context():
            archive_cid = generate_cid(hrx_content)
            create_cid_record(archive_cid, hrx_content)

        with app_with_gateway.test_client() as client:
            response = client.get(f"/gateway/hrx/{archive_cid}/index.html")

            assert response.status_code == 200
            data = response.data.decode("utf-8")

            # Relative links should be rewritten to use gateway path
            assert f"/gateway/hrx/{archive_cid}" in data

    def test_gateway_hrx_http_css_file(self, app_with_gateway):
        """Test that HRX gateway serves CSS files correctly."""
        css_content = """body {
    background-color: #1a1a2e;
    color: #eee;
}"""

        hrx_content = self._create_hrx_archive({
            "styles.css": css_content,
        })

        with app_with_gateway.app_context():
            archive_cid = generate_cid(hrx_content)
            create_cid_record(archive_cid, hrx_content)

        with app_with_gateway.test_client() as client:
            response = client.get(f"/gateway/hrx/{archive_cid}/styles.css")

            assert response.status_code == 200
            # CSS should be served
            assert b"background-color" in response.data


class TestGatewayManIntegration:
    """Integration tests for gateway configuration loading and routing.

    Note: These tests verify that:
    1. Gateway configuration loads correctly from the gateways variable
    2. The gateway routes to the correct server path
    3. The gateway handles unconfigured gateways properly

    These tests ensure that internal gateways (like `man`) execute without
    making outbound HTTP requests.
    """

    @pytest.fixture
    def app_with_gateway(self, tmp_path):
        """Create app with gateway server and gateways variable."""
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
                "LOAD_CIDS_IN_TESTS": True,
            }
        )

        # Load default boot CID to get gateway server and gateways variable
        boot_cid_file = Path(__file__).parent.parent.parent / "reference_templates" / "default.boot.cid"
        if not boot_cid_file.exists():
            pytest.skip("No default.boot.cid file found")

        boot_cid = boot_cid_file.read_text(encoding="utf-8").strip()

        with app.app_context():
            success, error = import_boot_cid(app, boot_cid)
            if not success:
                pytest.skip(f"Failed to import boot CID: {error}")

        return app

    def test_gateway_man_routes_to_man_server(self, app_with_gateway):
        """Test that /gateway/man/grep returns the man page without HTTP proxying."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/man/ls", follow_redirects=True)

            assert response.status_code == 200

            data = response.get_data(as_text=True)
            assert "<html" in data.lower(), (
                f"Expected HTML response wrapper for man gateway: {data[:500]}"
            )
            assert (
                "NAME" in data
                or "name" in data.lower()
                or "Command not found" in data
                or "ls" in data.lower()
            ), (
                "Expected man page content or an error page that still references the requested command. "
                f"Response was: {data[:500]}"
            )


class TestGatewayTldrIntegration:
    """Integration tests for the tldr gateway."""

    @pytest.fixture
    def app_with_gateway(self, tmp_path):
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
                "LOAD_CIDS_IN_TESTS": True,
            }
        )

        boot_cid_file = Path(__file__).parent.parent.parent / "reference_templates" / "default.boot.cid"
        if not boot_cid_file.exists():
            pytest.skip("No default.boot.cid file found")

        boot_cid = boot_cid_file.read_text(encoding="utf-8").strip()

        with app.app_context():
            success, error = import_boot_cid(app, boot_cid)
            if not success:
                pytest.skip(f"Failed to import boot CID: {error}")

        return app

    def test_gateway_tldr_routes_to_tldr_server(self, app_with_gateway):
        """Test that /gateway/tldr/ls returns an HTML page without HTTP proxying."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/tldr/ls", follow_redirects=True)
            assert response.status_code == 200

            data = response.get_data(as_text=True)
            assert "<html" in data.lower(), (
                f"Expected HTML response wrapper for tldr gateway: {data[:500]}"
            )
            assert "Gateway Not Found" not in data, (
                f"Gateway 'tldr' should be configured: {data[:500]}"
            )

    @pytest.mark.skipif(not shutil.which("tldr"), reason="tldr command not available")
    def test_gateway_tldr_grep_includes_linkified_pipeline_example(self, app_with_gateway):
        """Test that /gateway/tldr/grep includes the stdin pipeline example and linkifies commands."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/tldr/grep", follow_redirects=True)
            assert response.status_code == 200

            data = response.get_data(as_text=True)
            assert "<html" in data.lower(), (
                f"Expected HTML response wrapper for tldr gateway: {data[:500]}"
            )
            assert "/gateway/tldr/cat" in data, (
                f"Expected 'cat' to be linkified in grep page: {data[:500]}"
            )
            assert "/gateway/tldr/grep" in data, (
                f"Expected 'grep' to be linkified in grep page: {data[:500]}"
            )


class TestGatewayGeneralIntegration:
    """Integration tests for gateway pages that are not specific to a single gateway."""

    @pytest.fixture
    def app_with_gateway(self, tmp_path):
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
                "LOAD_CIDS_IN_TESTS": True,
            }
        )

        boot_cid_file = (
            Path(__file__).parent.parent.parent / "reference_templates" / "default.boot.cid"
        )
        if not boot_cid_file.exists():
            pytest.skip("No default.boot.cid file found")

        boot_cid = boot_cid_file.read_text(encoding="utf-8").strip()

        with app.app_context():
            success, error = import_boot_cid(app, boot_cid)
            if not success:
                pytest.skip(f"Failed to import boot CID: {error}")

        return app

    def test_gateway_ls_routes_to_man_server(self, app_with_gateway):
        """Test that /gateway/man/ls routes to /servers/man/ls."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/man/ls", follow_redirects=True)

            assert response.status_code == 200
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.data[:500]}"
            )

            data = response.data.decode("utf-8")

            # Man gateway should be configured
            assert "Gateway Not Found" not in data, (
                f"Gateway 'man' should be configured: {data[:500]}"
            )

    def test_gateway_instruction_page_lists_gateways(self, app_with_gateway):
        """Test that /gateway shows instruction page with configured gateways."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway", follow_redirects=True)

            assert response.status_code == 200

            data = response.data.decode("utf-8")

            # Should show Gateway Server page
            assert "Gateway" in data

            # Should list configured gateways (man, hrx, tldr, jsonplaceholder)
            assert "man" in data.lower() or "hrx" in data.lower(), (
                f"Should list configured gateways: {data[:500]}"
            )

    def test_gateway_unknown_returns_not_found(self, app_with_gateway):
        """Test that unknown gateway names return Gateway Not Found error."""
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/nonexistent/test", follow_redirects=True)

            assert response.status_code == 200

            data = response.data.decode("utf-8")

            # Should show "Gateway Not Found" for unconfigured gateway
            assert "Gateway Not Found" in data, (
                f"Should show 'Gateway Not Found' for unknown gateway: {data[:500]}"
            )


    def test_gateway_hrx_missing_archive_shows_root_cause_prominently(self, app_with_gateway):
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/hrx", follow_redirects=True)
            assert response.status_code == 200

            data = response.get_data(as_text=True)
            assert "Root cause" in data
            assert "HRX archive is required" in data
            head = data[:1200]
            assert "ValueError: HRX archive is required" in head


    def test_gateway_hrx_error_page_shows_archive_and_path(self, app_with_gateway):
        with app_with_gateway.test_client() as client:
            response = client.get("/gateway/hrx/foo/bar", follow_redirects=True)
            assert response.status_code == 200

            data = response.get_data(as_text=True)
            assert "Archive" in data
            assert "foo" in data
            assert "Path" in data
            assert "bar" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
