"""
Unit tests for documentation validation.

Tests that documentation files are valid, consistent, and provide accurate information.
"""

import os
import re
import unittest


class TestIsolationIssuesDocumentation(unittest.TestCase):
    """Test docs/test_isolation_issues.md documentation."""

    def setUp(self):
        """Set up test fixtures."""
        self.doc_path = 'docs/test_isolation_issues.md'
        if os.path.exists(self.doc_path):
            with open(self.doc_path, 'r') as f:
                self.content = f.read()
        else:
            self.content = None

    def test_documentation_file_exists(self):
        """Test that test isolation issues documentation exists."""
        self.assertTrue(os.path.exists(self.doc_path),
                       f"{self.doc_path} should exist")

    def test_documentation_has_markdown_header(self):
        """Test that documentation starts with a markdown header."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        # Check for level 1 header
        self.assertTrue(self.content.startswith('#'),
                       "Document should start with a markdown header")

    def test_documentation_mentions_timeout_removal(self):
        """Test that documentation mentions the timeout removal."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        # Check for mentions of timeout
        timeout_mentioned = 'timeout' in self.content.lower()
        self.assertTrue(timeout_mentioned,
                       "Documentation should mention timeout issues")

    def test_documentation_mentions_pytest(self):
        """Test that documentation mentions pytest."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        pytest_mentioned = 'pytest' in self.content.lower()
        self.assertTrue(pytest_mentioned,
                       "Documentation should mention pytest")

    def test_documentation_has_code_blocks(self):
        """Test that documentation contains code examples."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        # Check for markdown code blocks
        has_code_blocks = '```' in self.content
        self.assertTrue(has_code_blocks,
                       "Documentation should contain code examples")

    def test_documentation_proper_markdown_formatting(self):
        """Test that documentation uses proper markdown formatting."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        # Check for basic markdown elements
        has_headers = re.search(r'^#{1,6}\s+', self.content, re.MULTILINE)
        self.assertTrue(has_headers,
                       "Documentation should have markdown headers")

    def test_documentation_no_broken_internal_links(self):
        """Test that internal file references exist."""
        if self.content is None:
            self.skipTest(f"{self.doc_path} not found")
        
        # Find references to pytest.ini
        if 'pytest.ini' in self.content:
            self.assertTrue(os.path.exists('pytest.ini'),
                           "Referenced pytest.ini file should exist")
        
        # Find references to test files
        test_file_refs = re.findall(r'tests/test_\w+\.py', self.content)
        for ref in test_file_refs[:5]:  # Check first 5 references
            if os.path.exists(ref):
                self.assertTrue(True)
                break


class TestCheckRoutesScript(unittest.TestCase):
    """Test check_routes.py script functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.script_path = 'tests/check_routes.py'
        if os.path.exists(self.script_path):
            with open(self.script_path, 'r') as f:
                self.content = f.read()
        else:
            self.content = None

    def test_check_routes_file_exists(self):
        """Test that check_routes.py exists."""
        self.assertTrue(os.path.exists(self.script_path),
                       f"{self.script_path} should exist")

    def test_check_routes_is_executable_script(self):
        """Test that check_routes.py has shebang."""
        if self.content is None:
            self.skipTest(f"{self.script_path} not found")
        
        self.assertTrue(self.content.startswith('#!/usr/bin/env python'),
                       "Script should have proper shebang")

    def test_check_routes_has_docstring(self):
        """Test that check_routes.py has a module docstring."""
        if self.content is None:
            self.skipTest(f"{self.script_path} not found")
        
        # Check for docstring
        has_docstring = '"""' in self.content or "'''" in self.content
        self.assertTrue(has_docstring,
                       "Script should have a docstring")

    def test_check_routes_sets_up_environment(self):
        """Test that check_routes.py sets up proper environment."""
        if self.content is None:
            self.skipTest(f"{self.script_path} not found")
        
        # Check for environment variable setup
        self.assertIn('os.environ', self.content,
                     "Script should set up environment variables")
        self.assertIn('DATABASE_URL', self.content,
                     "Script should set DATABASE_URL")

    def test_check_routes_imports_app(self):
        """Test that check_routes.py imports the app."""
        if self.content is None:
            self.skipTest(f"{self.script_path} not found")
        
        self.assertIn('from app import app', self.content,
                     "Script should import Flask app")

    def test_check_routes_has_error_handling(self):
        """Test that check_routes.py has proper error handling."""
        if self.content is None:
            self.skipTest(f"{self.script_path} not found")
        
        has_try_except = 'try:' in self.content and 'except' in self.content
        self.assertTrue(has_try_except,
                       "Script should have error handling")

    def test_check_routes_not_test_file(self):
        """Test that check_routes.py doesn't match test file pattern."""
        filename = os.path.basename(self.script_path)
        self.assertFalse(filename.startswith('test_'),
                        "check_routes.py should not be discovered as a test")


class TestMarkdownDocumentationQuality(unittest.TestCase):
    """Test general quality of markdown documentation."""

    def test_readme_exists(self):
        """Test that README.md exists."""
        self.assertTrue(os.path.exists('README.md'),
                       "README.md should exist")

    def test_readme_not_empty(self):
        """Test that README.md has content."""
        with open('README.md', 'r') as f:
            content = f.read()
        
        self.assertGreater(len(content), 100,
                          "README.md should have substantial content")

    def test_agents_doc_exists(self):
        """Test that AGENTS.md exists."""
        self.assertTrue(os.path.exists('AGENTS.md'),
                       "AGENTS.md should exist")

    def test_test_index_exists(self):
        """Test that TEST_INDEX.md exists."""
        self.assertTrue(os.path.exists('TEST_INDEX.md'),
                       "TEST_INDEX.md should exist")

    def test_docs_directory_exists(self):
        """Test that docs directory exists."""
        self.assertTrue(os.path.isdir('docs'),
                       "docs/ directory should exist")


if __name__ == '__main__':
    unittest.main()