"""Integration tests for the URL Editor server."""

import pytest


class TestURLEditorIntegration:
    """Integration tests for the URL Editor server."""

    @pytest.fixture(autouse=True)
    def setup_urleditor_server(self, memory_db_app):
        """Set up the urleditor server in the test database."""
        with memory_db_app.app_context():
            # Load the urleditor server definition
            from pathlib import Path
            from models import Server
            from database import db

            urleditor_path = (
                Path(__file__).parent.parent.parent
                / "reference_templates"
                / "servers"
                / "definitions"
                / "urleditor.py"
            )
            with open(urleditor_path, "r", encoding="utf-8") as f:
                server_code = f.read()

            # Create the server in the database
            server = Server(name="urleditor", definition=server_code, enabled=True)
            db.session.add(server)
            db.session.commit()

    def test_urleditor_server_is_loaded(self, memory_client):
        """Test that the urleditor server is available."""
        response = memory_client.get("/servers")
        assert response.status_code == 200

        # Check that urleditor is in the response
        data = response.get_data(as_text=True)
        assert "urleditor" in data.lower()

    def test_urleditor_returns_html_page(self, memory_client):
        """Test that accessing /urleditor returns HTML."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        assert "<!DOCTYPE html>" in data or "<!doctype html>" in data
        assert "URL Editor" in data
        assert "url-editor" in data

    def test_urleditor_has_three_columns(self, memory_client):
        """Test that the URL Editor page has main sections."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        assert "editor-section" in data
        assert "indicators-section" in data
        # preview-section has been removed; now using final-preview-section
        assert "final-preview-section" in data

    def test_urleditor_includes_ace_editor(self, memory_client):
        """Test that the URL Editor page includes Ace editor."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        assert "ace.edit" in data
        assert "url-editor" in data

    def test_urleditor_has_action_buttons(self, memory_client):
        """Test that the URL Editor page has action buttons."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        assert "Copy URL" in data
        assert "Open URL" in data

    def test_urleditor_subpath_redirects(self, memory_client):
        """Test that accessing urleditor with subpath redirects to fragment."""
        response = memory_client.get("/urleditor/echo/test", follow_redirects=False)

        # Should get a redirect (the system redirects through CID)
        assert response.status_code in [301, 302, 303, 307, 308]

        # Check the Location header exists
        location = response.headers.get("Location", "")
        assert location  # Just verify we got a redirect location
        # Note: The redirect goes through CID, which is the expected behavior

    def test_urleditor_rejects_chained_input(self, memory_client, memory_db_app):
        """Test that urleditor rejects being used in a server chain."""
        # First, create a test server that outputs something
        with memory_db_app.app_context():
            from models import Server
            from database import db

            test_server_code = """
def main():
    return {"output": "test-output", "content_type": "text/plain"}
"""

            # Create the test server
            server = Server(
                name="urleditor-chain-test", definition=test_server_code, enabled=True
            )
            db.session.add(server)
            db.session.commit()

        # Try to chain urleditor after the test server
        # This should fail because urleditor doesn't support chaining
        response = memory_client.get(
            "/urleditor/urleditor-chain-test", follow_redirects=True
        )

        # The response should indicate that chaining is not supported
        data = response.get_data(as_text=True)
        # Either we get a redirect (which is fine) or an error message
        # We just verify it doesn't execute the chain successfully
        assert (
            response.status_code in [302, 400, 404]
            or "does not support" in data.lower()
        )

    def test_urleditor_content_type(self, memory_client):
        """Test that urleditor returns HTML content type."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type or "html" in content_type.lower()

    def test_urleditor_javascript_initialization(self, memory_client):
        """Test that the URL Editor JavaScript is properly initialized."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for key JavaScript components
        assert "URLEditorApp" in data
        assert "normalizeUrl" in data
        assert "updateFromEditor" in data
        assert "window.location.hash" in data

    def test_urleditor_has_indicators_section(self, memory_client):
        """Test that the URL Editor has indicators section."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        assert "Line Indicators" in data
        assert "indicators-list" in data

    def test_urleditor_has_preview_section(self, memory_client):
        """Test that the URL Editor has Final Output Preview section."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Line Previews section has been removed and merged into Line Indicators
        assert "Line Previews" not in data
        assert "preview-list" not in data
        # Final Output Preview should still exist at the bottom
        assert "Final Output Preview" in data
        assert "final-output" in data

    def test_urleditor_uses_meta_endpoint(self, memory_client):
        """Test that the URL Editor JavaScript uses the /meta endpoint."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for the new fetchMetadata function that queries /meta
        assert "fetchMetadata" in data
        assert "/meta/" in data
        assert "updateIndicatorsFromMetadata" in data

    def test_urleditor_verbose_hover_text(self, memory_client):
        """Test that the URL Editor has verbose hover text for indicators."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for verbose hover text descriptions
        assert (
            "this is a valid URL path segment" in data
            or "valid URL path segment" in data
        )
        assert "can accept chained input" in data or "chaining" in data.lower()

    def test_urleditor_view_links_cumulative_paths(self, memory_client):
        """Test that View links show cumulative paths from current line to end."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check that the JavaScript builds cumulative paths correctly
        # The View link should use lines.slice(index) to get segments from current to end
        assert "lines.slice(index)" in data or "slice(index)" in data
        assert "urlSegments.join" in data

    def test_urleditor_input_preview_functionality(self, memory_client):
        """Test that the Input Preview column fetches input from next segments."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check that input preview logic fetches from next segments
        assert "index < lines.length - 1" in data or "next segment" in data.lower()
        assert "lines.slice(index + 1)" in data or "slice(index + 1)" in data
        # Preview element should be updated
        assert "preview-" in data

    def test_urleditor_view_link_structure(self, memory_client):
        """Test that View links have correct HTML structure."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for link element creation with proper ID pattern
        assert "link-" in data
        assert "linkElement.href" in data or "href" in data

    def test_urleditor_has_status_indicator_column(self, memory_client):
        """Test that the URL Editor has a status indicator column."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for status indicator element in the row
        assert "status-" in data
        assert "indicator-status" in data

    def test_urleditor_status_indicator_css(self, memory_client):
        """Test that status indicator has proper CSS classes."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for status-related CSS classes
        assert "pending" in data
        assert "indicator-status" in data

    def test_urleditor_update_status_indicator_function(self, memory_client):
        """Test that updateStatusIndicator function exists."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check for the updateStatusIndicator function
        assert "updateStatusIndicator" in data
        assert "status-${index}" in data

    def test_urleditor_status_changes_on_fetch(self, memory_client):
        """Test that status indicator changes during fetch operations."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check that fetchPreviewData updates status
        assert "updateStatusIndicator" in data
        # Check for status transitions: pending -> success/failure
        assert "pending" in data
        assert "valid" in data or "success" in data.lower()
        assert "invalid" in data or "failure" in data.lower()

    def test_urleditor_failure_info_display(self, memory_client):
        """Test that failure information is displayed instead of preview on error."""
        response = memory_client.get("/urleditor", follow_redirects=True)
        assert response.status_code == 200

        data = response.get_data(as_text=True)
        # Check that preview element shows failure information on error
        assert "Failed:" in data or "Error:" in data
        assert "previewElement.textContent" in data
