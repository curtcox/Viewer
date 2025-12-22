"""Tests for help documentation routes and rendering."""

from flask import url_for


class TestHelpRoutes:
    """Test help documentation functionality."""

    def test_help_page_renders(self, memory_client):
        """Test that the help page renders successfully."""
        response = memory_client.get('/help')
        assert response.status_code == 200
        assert b'Help Documentation' in response.data

    def test_help_page_contains_main_sections(self, memory_client):
        """Test that help page includes all main documentation sections."""
        response = memory_client.get('/help')
        assert b'Aliases' in response.data
        assert b'Servers' in response.data
        assert b'Variables' in response.data
        assert b'Secrets' in response.data
        assert b'CIDs' in response.data
        assert b'Boot Images' in response.data
        assert b'Import' in response.data and b'Export' in response.data

    def test_help_page_contains_links_to_features(self, memory_client):
        """Test that help page includes links to app features."""
        response = memory_client.get('/help')
        # Check for links to main feature pages
        assert b'/aliases' in response.data
        assert b'/servers' in response.data
        assert b'/variables' in response.data
        assert b'/secrets' in response.data
        assert b'/export' in response.data
        assert b'/import' in response.data

    def test_help_page_contains_boot_image_info(self, memory_client):
        """Test that help page includes boot image documentation."""
        response = memory_client.get('/help')
        assert b'Boot Images' in response.data
        assert b'Default' in response.data
        assert b'Minimal' in response.data
        assert b'Readonly' in response.data

    def test_help_page_url_for_works(self, memory_db_app):
        """Test that url_for works for help_page route."""
        with memory_db_app.test_request_context():
            url = url_for('main.help_page')
            assert url == '/help'

    def test_help_markdown_renders_document(self, memory_client):
        """Help markdown endpoint renders docs as HTML."""
        response = memory_client.get("/help/help.md")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert '<main class="markdown-body">' in body
        assert '<a href="/aliases">' in body
        assert '/help/import-export-json-format.md' in body

    def test_help_markdown_rejects_traversal(self, memory_client):
        """Traversal attempts return 404."""
        response = memory_client.get("/help/../app.py")
        assert response.status_code == 404
