"""Unit tests for the run script.

These tests verify that the run script has proper error handling and
logic to handle missing .env files for commands that don't need them.
"""

import unittest
from pathlib import Path


class TestRunScriptContent(unittest.TestCase):
    """Tests for run script content and structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.run_script = self.project_root / 'run'

    def test_run_script_exists(self):
        """Test that run script exists."""
        self.assertTrue(self.run_script.exists(), "run script should exist")

    def test_run_script_is_executable(self):
        """Test that run script has executable permissions."""
        import os
        self.assertTrue(
            os.access(self.run_script, os.X_OK),
            "run script should be executable"
        )

    def test_run_script_has_bash_shebang(self):
        """Test that run script uses bash."""
        with open(self.run_script, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        self.assertIn('bash', first_line, "run script should use bash")

    def test_run_script_checks_for_help_flag(self):
        """Test that run script checks for --help flag before requiring .env."""
        content = self.run_script.read_text()

        # Should check for help flags
        self.assertIn('--help', content, "Should check for --help flag")
        self.assertIn('-h', content, "Should check for -h flag")

        # Should have logic to skip .env check for help
        self.assertIn('needs_env', content, "Should have needs_env logic")

    def test_run_script_checks_for_list_flag(self):
        """Test that run script checks for --list flag before requiring .env."""
        content = self.run_script.read_text()

        # Should check for list flag
        self.assertIn('--list', content, "Should check for --list flag")

    def test_run_script_has_env_error_handling(self):
        """Test that run script has enhanced error messages for missing .env."""
        content = self.run_script.read_text()

        # Should have error message about .env not found
        self.assertIn('.env file not found', content,
                     "Should have .env not found error message")

        # Should mention ./install
        self.assertIn('./install', content,
                     "Should mention ./install in error message")

        # Should mention .env.sample
        self.assertIn('.env.sample', content,
                     "Should mention .env.sample in error message")

    def test_run_script_has_env_source_error_handling(self):
        """Test that run script handles errors when sourcing .env file."""
        content = self.run_script.read_text()

        # Should handle errors when sourcing .env
        self.assertIn('Failed to load .env file', content,
                     "Should have error message for failed .env load")

        # Should mention syntax errors
        self.assertIn('syntax errors', content.lower(),
                     "Should mention syntax errors in error message")

    def test_run_script_warns_about_missing_venv(self):
        """Test that run script warns about missing venv for server commands."""
        content = self.run_script.read_text()

        # Should check for venv directory
        self.assertIn('venv', content, "Should check for venv directory")

        # Should have warning about missing venv
        self.assertIn('Warning', content, "Should have warning about missing venv")

    def test_run_script_uses_set_e(self):
        """Test that run script uses set -e for error handling."""
        content = self.run_script.read_text()

        # Should use set -e to exit on error
        self.assertIn('set -e', content,
                     "Should use 'set -e' for error handling")


class TestRunScriptErrorMessages(unittest.TestCase):
    """Tests for run script error message quality."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.run_script = self.project_root / 'run'
        self.content = self.run_script.read_text()

    def test_error_messages_use_stderr(self):
        """Test that error messages are directed to stderr."""
        # Error messages should use >&2
        self.assertIn('>&2', self.content,
                     "Error messages should be directed to stderr")

    def test_error_messages_are_clear_and_actionable(self):
        """Test that error messages provide clear actionable steps."""
        # Should have numbered steps
        self.assertIn('1.', self.content,
                     "Should have numbered steps in error messages")

        # Should tell users what to do
        self.assertIn('To fix this issue:', self.content,
                     "Should explain how to fix the issue")

    def test_env_error_explains_what_env_is_for(self):
        """Test that .env error explains what .env file is used for."""
        # Should explain what .env contains
        self.assertIn('environment variables', self.content.lower(),
                     "Should explain that .env contains environment variables")


class TestRunScriptLogic(unittest.TestCase):
    """Tests for run script conditional logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.run_script = self.project_root / 'run'
        self.content = self.run_script.read_text()

    def test_needs_env_defaults_to_true(self):
        """Test that needs_env variable defaults to true."""
        # Should default to requiring .env
        self.assertIn('needs_env=true', self.content,
                     "needs_env should default to true")

    def test_needs_env_set_to_false_for_help_list(self):
        """Test that needs_env is set to false for --help and --list."""
        # Should set needs_env=false in case statement
        lines = self.content.split('\n')

        found_case = False
        found_needs_env_false = False

        for i, line in enumerate(lines):
            if 'case' in line and '$*' in line:
                found_case = True
            if found_case and 'needs_env=false' in line:
                found_needs_env_false = True
                break

        self.assertTrue(found_needs_env_false,
                       "Should set needs_env=false in case statement")

    def test_only_sources_env_when_needed(self):
        """Test that .env is only sourced when needs_env is true."""
        # Should check needs_env before sourcing
        self.assertIn('if [ "$needs_env" = true ]', self.content,
                     "Should check needs_env before sourcing .env")


if __name__ == '__main__':
    unittest.main()
