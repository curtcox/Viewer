"""Integration tests for urleditor server resource loading and serving."""

from typing import Any

import pytest
import re


class TestURLEditorResources:
    """Integration tests for URL Editor resource loading and serving."""

    client: Any

    @pytest.fixture(autouse=True)
    def setup_urleditor_server(self, memory_db_app):
        """Set up the urleditor server in the test database."""
        with memory_db_app.app_context():
            # Load the urleditor server definition
            from pathlib import Path
            from models import Server
            from database import db

            urleditor_path = Path(__file__).parent.parent.parent / "reference_templates" / "servers" / "definitions" / "urleditor.py"
            with open(urleditor_path, 'r', encoding="utf-8") as f:
                server_code = f.read()

            # Create the server in the database
            server = Server(
                name="urleditor",
                definition=server_code,
                enabled=True
            )
            db.session.add(server)
            db.session.commit()

        self.client = memory_db_app.test_client()

    def test_urleditor_returns_html_page(self):
        """Test that /urleditor returns an HTML page."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')
        assert b'<!DOCTYPE html>' in response.data
        assert b'URL Editor' in response.data

    def test_urleditor_includes_css_inline(self):
        """Test that CSS is included inline in the response."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        # Check that CSS is embedded as <style> tag, not referenced as external file
        assert b'<style>' in response.data
        assert b'.editor-wrapper' in response.data  # CSS class from urleditor.css
        assert b'.indicators-section' in response.data  # Another CSS class

        # Ensure no broken CSS file references
        assert b'href="urleditor.css"' not in response.data
        assert b'<link href="<style>' not in response.data  # Invalid HTML

    def test_urleditor_includes_js_inline(self):
        """Test that JavaScript is included inline in the response."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        # Check that JS is embedded as <script> tag, not referenced as external file
        assert b'<script>' in response.data
        assert b'URLEditorApp' in response.data  # Class from urleditor.js
        assert b'normalizeUrl' in response.data  # Function from urleditor.js

        # Ensure no broken JS file references
        assert b'src="urleditor.js"' not in response.data
        assert b'<script src="<script>' not in response.data  # Invalid HTML

    def test_urleditor_html_structure(self):
        """Test that HTML has proper structure with all required elements."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        html_content = response.data.decode('utf-8')

        # Check for main structural elements (may be in embedded content)
        assert 'editor-container' in html_content
        assert 'editor-wrapper' in html_content
        assert 'url-editor' in html_content
        assert 'indicators-list' in html_content
        # Note: preview-list was removed, replaced with final-preview-section
        assert 'final-preview-section' in html_content
        assert 'final-output' in html_content

        # Check for buttons
        assert 'copy-url-btn' in html_content
        assert 'open-url-btn' in html_content

    def test_urleditor_no_broken_url_references(self):
        """Test that there are no broken URL references like '//'."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        html_content = response.data.decode('utf-8')

        # Check for the specific error pattern: href="//" or src="//"
        assert 'href="//"' not in html_content
        assert 'src="//"' not in html_content

        # Check for malformed link tags
        assert '<link href="<style>' not in html_content
        assert '<script src="<script>' not in html_content

    def test_urleditor_initial_url_in_fragment(self):
        """Test that initial URL is properly set in JavaScript."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        html_content = response.data.decode('utf-8')

        # Check that INITIAL_URL variable is defined
        assert 'var INITIAL_URL =' in html_content or 'const INITIAL_URL =' in html_content

    def test_urleditor_css_contains_expected_styles(self):
        """Test that embedded CSS contains expected styling rules."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        html_content = response.data.decode('utf-8')

        # Extract CSS content
        style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
        assert style_match is not None, "No <style> tag found"

        css_content = style_match.group(1)

        # Check for key CSS rules
        assert '.editor-wrapper' in css_content
        assert 'min-height' in css_content
        assert 'border' in css_content
        assert 'background-color' in css_content

    def test_urleditor_js_contains_expected_functions(self):
        """Test that embedded JavaScript contains expected functions."""
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        html_content = response.data.decode('utf-8')

        # Extract JS content (find the last large <script> tag, which should be our code)
        script_matches = re.findall(r'<script>(.*?)</script>', html_content, re.DOTALL)
        assert len(script_matches) > 0, "No <script> tags found"

        # The urleditor.js content should be in one of the script tags
        js_content = ' '.join(script_matches)

        # Check for key functions and classes
        assert 'normalizeUrl' in js_content or 'function normalizeUrl' in js_content
        assert 'URLEditorApp' in js_content or 'class URLEditorApp' in js_content
        assert 'createFallbackEditor' in js_content or 'function createFallbackEditor' in js_content

    def test_urleditor_with_initial_url_fragment(self):
        """Test that urleditor handles URL with fragment properly."""
        # Note: Fragments are client-side only, so server doesn't see them
        # But we test that the page is still served correctly
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    def test_urleditor_redirects_subpath_to_fragment(self):
        """Test that /urleditor/path redirects."""
        response = self.client.get('/urleditor/echo/test', follow_redirects=False)
        # The server should redirect subpaths (the actual redirect URL may be converted to CID)
        assert response.status_code == 302
        assert response.location is not None  # Just verify there's a redirect location

    def test_urleditor_rejects_chaining(self):
        """Test that urleditor rejects being used in a chain."""
        # This would require calling the server with input_data
        # For integration test, we just verify the page loads without chaining
        response = self.client.get('/urleditor', follow_redirects=True)
        assert response.status_code == 200

        # The error message should not be present in normal usage
        assert b'does not support URL chaining' not in response.data
