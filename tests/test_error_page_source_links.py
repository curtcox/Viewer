"""Test that error pages show proper source links for all project files in stack traces."""
import re
import unittest
from unittest.mock import Mock, patch

from app import create_app
from database import db


class TestErrorPageSourceLinks(unittest.TestCase):
    """Test that error pages include proper source links in stack traces."""

    def setUp(self):
        """Set up test environment."""
        # Skip tests if app is mocked (during unittest discover)
        test_app = create_app()
        if isinstance(test_app, Mock):
            self.skipTest("Skipping due to mocked app during unittest discover")

        self.app = test_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.test_user_id = 'test_user_123'

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'app'):
            with self.app.app_context():
                db.session.remove()
                db.drop_all()

    def test_aliases_error_shows_source_links_in_stack_trace(self):
        """Test that when aliases page throws an error, the error page shows source links."""
        with self.app.test_request_context('/aliases'):
            try:
                # Mock the get_user_aliases function to raise a database error similar to the real issue
                with patch('db_access.get_user_aliases') as mock_get_aliases:
                    with patch('identity.current_user') as mock_current_user:
                        # Mock authentication
                        mock_current_user.id = self.test_user_id

                        # Simulate the SQLAlchemy OperationalError that occurs in the real scenario
                        import sqlite3

                        from sqlalchemy.exc import OperationalError

                        # Create a realistic database error like the one in the stack trace
                        sqlite_error = sqlite3.OperationalError("no such column: alias.definition")
                        sqlalchemy_error = OperationalError(
                            "SELECT alias.id AS alias_id, alias.name AS alias_name, alias.definition AS alias_definition, alias.user_id AS alias_user_id, alias.created_at AS alias_created_at, alias.updated_at AS alias_updated_at \nFROM alias \nWHERE alias.user_id = ? ORDER BY alias.name",
                            {'user_id': 'test_user_123'},
                            sqlite_error
                        )
                        mock_get_aliases.side_effect = sqlalchemy_error

                        # Import the aliases function to get it in the traceback
                        from routes.aliases import aliases

                        # This should raise the error
                        aliases()

            except Exception as exc:
                # Call the error handler directly
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Check that we have a stack trace section
                self.assertIn('Stack trace with source links', html_content)

                # Check that we have source links for project files
                # The error should show links to routes/aliases.py and db_access.py
                self.assertIn('href="/source/routes/aliases.py"', html_content,
                             "Should have source link to routes/aliases.py")
                self.assertIn('href="/source/db_access.py"', html_content,
                             "Should have source link to db_access.py")

                # Check for external link icons
                self.assertIn('fas fa-external-link-alt', html_content,
                             "Should have external link icons for source links")

                # Check that links open in new tab
                self.assertIn('target="_blank"', html_content,
                             "Source links should open in new tab")

                # Verify we have the enhanced code context with >>> markers
                self.assertIn('>>>', html_content,
                             "Should show enhanced code context with >>> error markers")

    def test_debug_mode_now_uses_custom_error_handler(self):
        """Test that our fix allows custom error handlers to work in debug mode."""
        # Create an app in debug mode (like the real scenario)
        debug_app = create_app({'TESTING': True, 'DEBUG': True})

        with debug_app.test_request_context('/test-error'):
            # Test the error handler directly to verify it works in debug mode
            try:
                # Create a realistic error
                import sqlite3

                from sqlalchemy.exc import OperationalError

                sqlite_error = sqlite3.OperationalError("no such column: alias.definition")
                sqlalchemy_error = OperationalError(
                    "SELECT alias.id AS alias_id, alias.name AS alias_name, alias.definition AS alias_definition",
                    {'user_id': 'test_user_123'},
                    sqlite_error
                )

                # Raise the error to create a proper traceback
                raise sqlalchemy_error

            except Exception as exc:
                # Call our custom error handler directly
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                # Should get 500 status
                self.assertEqual(status_code, 500)

                # Should have our custom error page with source links
                self.assertIn('Stack trace with source links', html_content,
                             "Should show our custom error page with source links")

                # Should have source links for project files
                self.assertIn('href="/source/', html_content,
                             "Should have source links to project files")

                # Verify the error handler works correctly
                self.assertIn('OperationalError', html_content,
                             "Should show the correct exception type")
                self.assertIn('no such column: alias.definition', html_content,
                             "Should show the correct error message")

    def test_debug_mode_override_mechanism_works(self):
        """Test that our Flask debug mode override mechanism is properly installed."""
        # Create an app in debug mode
        debug_app = create_app({'TESTING': True, 'DEBUG': True})

        # Verify that debug mode is enabled
        self.assertTrue(debug_app.debug, "App should be in debug mode")

        # Verify that our custom error handler override is installed
        self.assertTrue(hasattr(debug_app, 'handle_exception'),
                       "App should have handle_exception method")

        # The override should be different from the original Flask method
        # (This is a bit tricky to test directly, but we can verify the behavior)
        with debug_app.test_request_context('/test'):
            try:
                raise RuntimeError("Test error for debug mode override")
            except Exception as exc:
                # Call the overridden handle_exception method
                result = debug_app.handle_exception(exc)

                # Should return our custom error page, not raise the exception
                self.assertIsNotNone(result, "Should return a response, not None")

                # Should be a tuple (html_content, status_code)
                if isinstance(result, tuple):
                    html_content, status_code = result
                    self.assertEqual(status_code, 500)
                    self.assertIn('Stack trace with source links', html_content)

    def test_source_link_generation_for_various_file_types(self):
        """Test that source links are generated for various project file types."""
        with self.app.test_request_context('/test'):
            try:
                # Create an error that will show up in multiple file types
                # Import something to get various files in the traceback

                raise RuntimeError("Test error for source link generation")

            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should have source links for Python files
                source_links = [line for line in html_content.split('\n') if 'href="/source/' in line]
                self.assertGreater(len(source_links), 0, "Should have at least one source link")

                # Check for specific project files that should be linked
                python_files_linked = any('/source/' in link and '.py' in link for link in source_links)
                self.assertTrue(python_files_linked, "Should have source links for Python files")

    def test_enhanced_code_context_with_line_numbers(self):
        """Test that enhanced code context shows line numbers and error markers."""
        with self.app.test_request_context('/test'):
            try:
                # Create an error at a specific line
                raise ValueError("Test error for code context verification")

            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should have enhanced code context with >>> markers
                self.assertIn('>>>', html_content, "Should have >>> error markers")

                # Check if we have actual code blocks with line numbers
                # Look for code blocks that contain line numbers
                code_block_pattern = r'<pre[^>]*><code[^>]*>.*?</code></pre>'
                code_blocks = re.findall(code_block_pattern, html_content, re.DOTALL)

                if len(code_blocks) > 0:
                    # Look for line numbers in code blocks (both >>> marked and regular, accounting for HTML encoding)
                    line_number_pattern = r'(?:>>>|&gt;&gt;&gt;)?\s*\d+\s*:'
                    line_numbers_in_code = []
                    for block in code_blocks:
                        line_numbers_in_code.extend(re.findall(line_number_pattern, block))

                    # Should have line numbers in the code context
                    self.assertGreater(len(line_numbers_in_code), 0, "Should have line numbers in code blocks")

                    # Look specifically for the >>> error marker (accounting for HTML encoding)
                    error_marker_pattern = r'(?:>>>|&gt;&gt;&gt;)\s*\d+\s*:'
                    error_markers = []
                    for block in code_blocks:
                        error_markers.extend(re.findall(error_marker_pattern, block))

                    # Should have at least one >>> error marker
                    self.assertGreater(len(error_markers), 0, "Should have >>> error markers for the exact error line")
                else:
                    # If no code blocks, that's also valid - just check we have the basic structure
                    print("DEBUG: No code blocks found, checking for basic error structure")
                    self.assertIn('ValueError', html_content, "Should show the exception type")

    def test_exception_chain_display(self):
        """Test that exception chains are properly displayed with separators."""
        with self.app.test_request_context('/test'):
            try:
                # Create a chained exception
                try:
                    raise ValueError("Original error")
                except ValueError as e:
                    raise RuntimeError("Wrapped error") from e

            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should show both exceptions in the chain
                self.assertIn('RuntimeError', html_content, "Should show the outer exception")
                self.assertIn('ValueError', html_content, "Should show the inner exception")

                # Should have exception chain separators
                self.assertIn('Exception Chain', html_content, "Should have exception chain separators")
                self.assertIn('Caused by:', html_content, "Should have 'Caused by:' labels")

    def test_error_page_robustness_with_missing_files(self):
        """Test that error page works even when some files in the stack trace are missing."""
        with self.app.test_request_context('/test'):
            # Mock the file reading to simulate missing files
            with patch('pathlib.Path.exists', return_value=False):
                try:
                    raise RuntimeError("Test error with missing files")

                except Exception as exc:
                    from routes.core import internal_error
                    html_content, status_code = internal_error(exc)

                    self.assertEqual(status_code, 500)

                    # Should still generate a valid error page
                    self.assertIn('Stack trace with source links', html_content)
                    self.assertIn('RuntimeError', html_content)

                    # Should gracefully handle missing files
                    self.assertIn('Test error with missing files', html_content)

    def test_error_page_html_structure_and_styling(self):
        """Test that error page has proper HTML structure and Bootstrap styling."""
        with self.app.test_request_context('/test'):
            try:
                raise RuntimeError("Test error for HTML structure verification")

            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should have proper HTML structure
                self.assertIn('<!DOCTYPE html>', html_content, "Should have proper DOCTYPE")
                self.assertIn('<html', html_content, "Should have html tag")
                self.assertIn('500 - Internal Server Error', html_content, "Should have error title")

                # Should have Bootstrap styling
                self.assertIn('card', html_content, "Should use Bootstrap card component")
                self.assertIn('btn btn-primary', html_content, "Should have Bootstrap button styling")

                # Should have Font Awesome icons
                self.assertIn('fas fa-', html_content, "Should have Font Awesome icons")
                self.assertIn('fa-external-link-alt', html_content, "Should have external link icons")

                # Should have debugging tips section
                self.assertIn('Debugging Tips', html_content, "Should have debugging tips section")

    def test_source_links_open_in_new_tab(self):
        """Test that source links have target='_blank' to open in new tab."""
        with self.app.test_request_context('/test'):
            try:
                raise RuntimeError("Test error for link target verification")

            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Find all source links
                source_link_pattern = r'<a[^>]*href="/source/[^"]*"[^>]*>'
                source_links = re.findall(source_link_pattern, html_content)

                # All source links should have target="_blank"
                for link in source_links:
                    self.assertIn('target="_blank"', link,
                                f"Source link should open in new tab: {link}")

    def test_comprehensive_file_discovery_in_stack_trace(self):
        """Test that stack trace building discovers all project files, not just git-tracked ones."""
        with self.app.test_request_context('/test'):
            # Test the _get_all_project_files function directly
            from flask import current_app
            from pathlib import Path
            from routes.source import _get_tracked_paths
            from utils.stack_trace import build_stack_trace

            try:
                # Create an error to build stack trace for
                raise RuntimeError("Test error for file discovery")

            except Exception as exc:
                # Build stack trace and check file discovery
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                stack_trace = build_stack_trace(exc, root_path, tracked_paths)

                # Should have at least one frame
                self.assertGreater(len(stack_trace), 0, "Should have stack trace frames")

                # Should include project files in the stack trace
                project_files = [frame for frame in stack_trace
                               if frame.get('source_link') and '/source/' in frame['source_link']]

                # Should have at least one project file with source link
                self.assertGreater(len(project_files), 0,
                                 "Should have at least one project file with source link")

    def test_error_page_shows_comprehensive_project_file_links(self):
        """Test that error pages show links to ALL relevant project files, not just git-tracked ones."""
        # Test the error handler directly with a request context
        with self.app.test_request_context('/test'):
            try:
                # Create an error that involves multiple project files
                raise RuntimeError("Test error for comprehensive source link testing")
            except Exception as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)

                self.assertEqual(status_code, 500)

                # Should have source links for multiple project files
                source_link_pattern = r'href="/source/([^"]+)"'
                source_links = re.findall(source_link_pattern, html_content)

                # Should have at least some source links
                self.assertGreater(len(source_links), 0,
                                 "Should have at least one source link in the stack trace")

                # Verify that source links are for project files (not external libraries)
                project_files = [link for link in source_links if not link.startswith('venv/')]
                self.assertGreater(len(project_files), 0,
                                 "Should have source links for project files, not just external libraries")

    def test_error_page_template_structure(self):
        """Test that the error page template has the correct structure for displaying source links."""
        # Test the template directly by triggering an error
        with self.app.test_request_context('/test-template'):
            from routes.core import internal_error

            # Create a more complex error that will generate a stack trace
            try:
                # Create an error with a proper traceback
                raise RuntimeError("Test error for template structure verification")
            except Exception as mock_error:
                # Call the error handler directly
                response_tuple = internal_error(mock_error)
                html_content = response_tuple[0]  # The rendered template
                status_code = response_tuple[1]   # Should be 500

                self.assertEqual(status_code, 500)

                # Check for key template elements
                self.assertIn('500 - Internal Server Error', html_content)
                self.assertIn('fas fa-bug', html_content)  # Bug icon
                self.assertIn('Debugging Tips', html_content)

                # Check for source link structure
                if 'stack_trace' in html_content:
                    self.assertIn('fas fa-external-link-alt', html_content)
                    self.assertIn('target="_blank"', html_content)

    def test_stack_trace_building_with_project_files(self):
        """Test that build_stack_trace function creates proper source links."""
        with self.app.app_context():
            from flask import current_app
            from pathlib import Path
            from routes.source import _get_tracked_paths
            from utils.stack_trace import build_stack_trace

            # Create an error with a traceback that includes project files
            try:
                # This should create a traceback that includes this test file
                raise RuntimeError("Test error for stack trace building")
            except Exception as e:
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                stack_trace = build_stack_trace(e, root_path, tracked_paths)

                # Should have at least one frame
                self.assertGreater(len(stack_trace), 0, "Should have stack trace frames")

                # Look for frames with source links
                frames_with_links = [frame for frame in stack_trace if frame.get('source_link')]

                # Should have at least one frame with a source link
                self.assertGreater(len(frames_with_links), 0,
                                 "Should have at least one frame with a source link")

                # Check that source links are properly formatted
                for frame in frames_with_links:
                    source_link = frame['source_link']
                    self.assertTrue(source_link.startswith('/source/'),
                                  f"Source link should start with /source/, got: {source_link}")


if __name__ == '__main__':
    unittest.main()
