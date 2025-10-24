#!/usr/bin/env python3
"""Test script to verify enhanced error page functionality with comprehensive source links."""

import unittest
from unittest.mock import patch

from app import create_app
from database import db
from routes.core import _build_stack_trace, internal_error
from routes.source import _get_comprehensive_paths


class TestEnhancedErrorPageIntegration(unittest.TestCase):
    """Integration tests for enhanced error page system."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })
        self.app.config['PROPAGATE_EXCEPTIONS'] = False

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_aliases_route_error_shows_comprehensive_source_links(self):
        """Test that error pages show comprehensive source links for all project files."""
        with self.app.test_request_context('/test'):
            try:
                # Create a simple error that will have this test file in the traceback
                raise RuntimeError('Test error for comprehensive source links')
            except RuntimeError as exc:
                response, status = internal_error(exc)

                self.assertEqual(status, 500)

                # Verify the error page contains basic error info
                self.assertIn('RuntimeError', response)
                self.assertIn('Test error for comprehensive source links', response)

                # Should have source link to this test file
                self.assertIn('href="/source/tests/test_enhanced_error_pages.py"', response)

                # Should show enhanced code context with >>> markers
                self.assertIn('>>>', response)

                # Verify the enhanced error page structure
                self.assertIn('Stack trace with source links', response)
                self.assertIn('target="_blank"', response)  # Links should open in new tab

    def test_comprehensive_file_discovery_includes_all_project_files(self):
        """Test that comprehensive file discovery includes all project files, not just git-tracked."""
        with self.app.app_context():
            comprehensive_paths = _get_comprehensive_paths(self.app.root_path)

            # Should include Python files
            self.assertTrue(any('routes/aliases.py' in path for path in comprehensive_paths))
            self.assertTrue(any('routes/core.py' in path for path in comprehensive_paths))

            # Should include template files
            self.assertTrue(any('.html' in path for path in comprehensive_paths))

            # Should include this test file
            self.assertTrue(
                any('tests/test_enhanced_error_pages.py' in path for path in comprehensive_paths)
            )

    def test_error_page_template_renders_with_source_links(self):
        """Test that the 500.html template properly renders source links."""
        with self.app.test_request_context('/test'):
            try:
                # Create a traceback that includes multiple project files
                raise ValueError('Test error for template rendering')
            except ValueError as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)

        # Check for proper HTML structure
        self.assertIn('<div class="card-header bg-danger text-white">', response)
        self.assertIn('<i class="fas fa-bug me-2"></i>', response)
        self.assertIn('Exception:', response)
        self.assertIn('ValueError', response)

        # Check for source link icons and styling
        self.assertIn('<i class="fas fa-external-link-alt me-1 text-primary"></i>', response)
        self.assertIn('target="_blank"', response)

        # Check for debugging tips section
        self.assertIn('Debugging Tips:', response)
        self.assertIn('Click the', response)
        self.assertIn('links to view source code', response)

    def test_exception_chain_display_with_separators(self):
        """Test that exception chains are displayed with proper visual separators."""
        with self.app.app_context():
            try:
                try:
                    raise ValueError('Original error')
                except ValueError as e:
                    raise RuntimeError('Chained error') from e
            except RuntimeError as exc:
                frames = _build_stack_trace(exc)

        # Should have separator frames for exception chain
        separator_frames = [f for f in frames if f.get('is_separator', False)]
        self.assertTrue(len(separator_frames) > 0)

        # Check separator styling and content
        separator = separator_frames[0]
        self.assertIn('Exception Chain', separator['display_path'])
        self.assertIn('ValueError', separator['function'])
        self.assertIsNone(separator['source_link'])

    def test_source_browser_serves_comprehensive_files(self):
        """Test that source browser can serve files discovered by comprehensive file discovery."""
        with self.app.test_client() as client:
            # Test accessing a Python file
            response = client.get('/source/routes/aliases.py')
            self.assertIn(response.status_code, [200, 302])  # 200 for file, 302 for redirect to login

            # Test accessing a template file
            response = client.get('/source/templates/500.html')
            self.assertIn(response.status_code, [200, 302])

    def test_error_handling_robustness(self):
        """Test that error handling is robust even when stack trace building fails."""
        with self.app.test_request_context('/test'):
            # Mock _build_stack_trace to fail
            with patch('routes.core._build_stack_trace', side_effect=Exception('Stack trace building failed')):
                try:
                    raise ValueError('Original error')
                except ValueError as exc:
                    response, status = internal_error(exc)

        self.assertEqual(status, 500)

        # Should still show basic error information
        self.assertIn('ValueError', response)
        self.assertIn('Original error', response)

        # Should show fallback error information
        self.assertIn('Stack trace generation failed', response)


if __name__ == '__main__':
    unittest.main()
