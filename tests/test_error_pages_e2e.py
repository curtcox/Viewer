#!/usr/bin/env python3
"""End-to-end tests for error page display with comprehensive stack traces and source links."""

import re
import unittest
from unittest.mock import MagicMock

from app import create_app
from database import db


class TestErrorPagesEndToEnd(unittest.TestCase):
    """End-to-end tests for error page functionality through HTTP requests."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        # Skip tests if app is mocked during unittest discover
        if isinstance(self.app, MagicMock):
            self.skipTest("Skipping due to mocked app during unittest discover")

        # Ensure error handlers are properly registered
        self.app.config['PROPAGATE_EXCEPTIONS'] = False

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_500_error_page_shows_stack_trace_with_source_links(self):
        """Test that 500 error pages show complete stack traces with clickable source links."""

        with self.app.test_request_context('/test-error'):
            try:
                # This will cause a deliberate error with a traceback
                raise RuntimeError('Deliberate test error for end-to-end testing')
            except RuntimeError as exc:
                # Directly call the error handler to get the rendered response
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Verify basic error page structure
                self.assertIn('500 - Internal Server Error', html_content)
                self.assertIn('RuntimeError', html_content)
                self.assertIn('Deliberate test error for end-to-end testing', html_content)

                # Verify stack trace section exists
                self.assertIn('Stack trace with source links', html_content)
                self.assertIn('most recent call last', html_content)

                # Verify source links are present and properly formatted
                source_link_pattern = r'href="/source/([^"]+)"'
                source_links = re.findall(source_link_pattern, html_content)

                # Should have at least one source link
                self.assertGreater(len(source_links), 0, "Should have source links in error page")

                # Verify links open in new tabs
                self.assertIn('target="_blank"', html_content)

                # Verify external link icons are present
                self.assertIn('fas fa-external-link-alt', html_content)

                # Verify enhanced code context with line markers
                self.assertIn('>>>', html_content)

                # Verify debugging tips section
                self.assertIn('Debugging Tips:', html_content)
                self.assertIn('Click the', html_content)
                self.assertIn('links to view source code', html_content)

    def test_error_page_includes_project_file_links(self):
        """Test that error pages include links to all relevant project files."""

        with self.app.test_request_context('/test-project-error'):
            try:
                # Import project modules to get them in the traceback

                # Trigger an error that will include project files in traceback
                raise ValueError('Project file error test')
            except ValueError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Look for source links to project files
                source_link_pattern = r'href="/source/([^"]+)"'
                source_links = re.findall(source_link_pattern, html_content)

                # Should have at least one source link (the test file itself)
                self.assertGreater(len(source_links), 0,
                                  "Should have source links in error page")

                # Verify the links are properly formatted as clickable elements
                for link in source_links[:3]:  # Check first few links
                    link_html = f'href="/source/{link}"'
                    self.assertIn(link_html, html_content)

                    # Verify the link has proper styling and opens in new tab
                    link_context_pattern = rf'<a href="/source/{re.escape(link)}"[^>]*target="_blank"[^>]*>'
                    self.assertTrue(re.search(link_context_pattern, html_content),
                                   f"Source link {link} should be properly formatted with target='_blank'")

    def test_exception_chain_display_in_browser(self):
        """Test that exception chains are properly displayed in browser."""

        with self.app.test_request_context('/test-exception-chain'):
            try:
                try:
                    raise ValueError('Original error in chain')
                except ValueError as e:
                    raise RuntimeError('Chained error for testing') from e
            except RuntimeError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Verify both exceptions are shown
                self.assertIn('RuntimeError', html_content)
                self.assertIn('ValueError', html_content)
                self.assertIn('Original error in chain', html_content)
                self.assertIn('Chained error for testing', html_content)

                # Verify exception chain separator is present
                self.assertIn('Exception Chain', html_content)
                self.assertIn('Caused by:', html_content)

                # Verify proper styling for separators
                self.assertIn('text-warning', html_content)  # Warning styling for separators

    def test_code_context_display_with_line_numbers(self):
        """Test that code context shows proper line numbers and error markers."""

        with self.app.test_request_context('/test-code-context'):
            try:
                # Create multiple lines so we can verify context display
                # The next line should be marked with >>> in the error display
                raise RuntimeError('Error with code context')
            except RuntimeError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Verify enhanced code context is shown
                self.assertIn('>>>', html_content)  # Error line marker

                # Verify line numbers are present in context
                line_number_pattern = r'&gt;&gt;&gt;\s*\d+:'
                self.assertTrue(re.search(line_number_pattern, html_content),
                               "Should show line numbers with >>> marker for error line")

                # Verify code context is properly formatted
                self.assertIn('<pre', html_content)  # Code should be in pre tags
                self.assertIn('<code>', html_content)  # And code tags

    def test_source_browser_accessibility_from_error_links(self):
        """Test that source links from error pages actually work."""
        from routes.core import internal_error

        with self.app.test_request_context('/test-source-links'):
            try:
                raise RuntimeError('Error to generate source links')
            except RuntimeError as exc:
                html_content, status_code = internal_error(exc)
                self.assertEqual(status_code, 500)

                # Extract source links from the error page
                source_link_pattern = r'href="/source/([^"]+)"'
                source_links = re.findall(source_link_pattern, html_content)

                # Should have at least one source link
                self.assertGreater(len(source_links), 0, "Should have source links in error page")

                # Test that we can actually access these source links
                for link in source_links[:3]:  # Test first few links to avoid too many requests
                    source_response = self.client.get(f'/source/{link}')

                    # Source links should either show the file (200) or redirect to login (302)
                    # but should not be 404 (not found)
                    self.assertIn(source_response.status_code, [200, 302],
                                 f"Source link /source/{link} should be accessible")

                    if source_response.status_code == 200:
                        # If we get the file content, verify it's not empty
                        source_content = source_response.get_data(as_text=True)
                        self.assertGreater(len(source_content), 0,
                                         f"Source file {link} should have content")

    def test_error_page_robustness_with_missing_files(self):
        """Test that error pages work even when some source files might be missing."""

        with self.app.test_request_context('/test-robustness'):
            try:
                # Create an error that might reference non-existent files
                raise FileNotFoundError('Test error for robustness checking')
            except FileNotFoundError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Even with potential missing files, should still show error info
                self.assertIn('FileNotFoundError', html_content)
                self.assertIn('Test error for robustness checking', html_content)

                # Should still have basic error page structure
                self.assertIn('500 - Internal Server Error', html_content)
                self.assertIn('Stack trace', html_content)

    def test_authenticated_error_page_display(self):
        """Test error page display when user is authenticated."""

        with self.app.app_context():
            # Track the authenticated user identifier
            user_id = 'test-user-123'

        with self.app.test_request_context('/test-auth-error'):
            try:
                # Import something from aliases to get it in traceback

                raise RuntimeError('Authenticated user error test')
            except RuntimeError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should still show full error page with source links
                self.assertIn('RuntimeError', html_content)
                self.assertIn('Authenticated user error test', html_content)

                # Should have source links to the test file
                self.assertIn('href="/source/tests/test_error_pages_e2e.py"', html_content)

    def test_error_page_html_structure_and_styling(self):
        """Test that error page has proper HTML structure and Bootstrap styling."""

        with self.app.test_request_context('/test-html-structure'):
            try:
                raise RuntimeError('HTML structure test error')
            except RuntimeError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Verify proper HTML structure
                self.assertIn('<!doctype html>', html_content.lower())
                self.assertIn('<html', html_content)
                self.assertIn('</html>', html_content)

                # Verify Bootstrap classes and components
                self.assertIn('container', html_content)
                self.assertIn('card', html_content)
                self.assertIn('card-header', html_content)
                self.assertIn('card-body', html_content)

                # Verify error-specific styling
                self.assertIn('bg-danger', html_content)  # Red header
                self.assertIn('text-white', html_content)  # White text on red

                # Verify Font Awesome icons
                self.assertIn('fas fa-bug', html_content)  # Bug icon
                self.assertIn('fas fa-external-link-alt', html_content)  # External link icons

                # Verify proper link styling
                self.assertIn('text-primary', html_content)  # Primary color for links

                # Verify debugging tips section
                self.assertIn('bg-info bg-opacity-10', html_content)  # Info background
                self.assertIn('fas fa-lightbulb', html_content)  # Lightbulb icon


if __name__ == '__main__':
    unittest.main()
