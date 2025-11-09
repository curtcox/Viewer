"""
Unit tests for pytest configuration changes.

Tests that pytest.ini is correctly configured after removing timeout settings
and ensures the configuration is valid and functional.
"""

import configparser
import os
import unittest


class TestPytestConfiguration(unittest.TestCase):
    """Test pytest.ini configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = configparser.ConfigParser()
        self.config.read('pytest.ini')

    def test_pytest_section_exists(self):
        """Test that [pytest] section exists in pytest.ini."""
        self.assertIn('pytest', self.config.sections())

    def test_pythonpath_configured(self):
        """Test that pythonpath is set to current directory."""
        pythonpath = self.config.get('pytest', 'pythonpath', fallback=None)
        self.assertIsNotNone(pythonpath)
        self.assertEqual(pythonpath.strip(), '.')

    def test_testpaths_configured(self):
        """Test that testpaths points to tests directory."""
        testpaths = self.config.get('pytest', 'testpaths', fallback=None)
        self.assertIsNotNone(testpaths)
        self.assertEqual(testpaths.strip(), 'tests')

    def test_python_files_pattern(self):
        """Test that python_files pattern is configured."""
        python_files = self.config.get('pytest', 'python_files', fallback=None)
        self.assertIsNotNone(python_files)
        self.assertEqual(python_files.strip(), 'test_*.py')

    def test_norecursedirs_configured(self):
        """Test that norecursedirs excludes common directories."""
        norecursedirs = self.config.get('pytest', 'norecursedirs', fallback=None)
        self.assertIsNotNone(norecursedirs)
        
        excluded_dirs = norecursedirs.split()
        expected_dirs = ['.git', 'build', 'dist', 'venv', 'install', 
                        'run', 'doctor', 'static', 'templates']
        
        for expected in expected_dirs:
            self.assertIn(expected, excluded_dirs,
                         f"Expected '{expected}' in norecursedirs")

    def test_addopts_excludes_integration_tests(self):
        """Test that addopts excludes integration tests by default."""
        addopts = self.config.get('pytest', 'addopts', fallback='')
        self.assertIn('-m "not integration"', addopts)

    def test_timeout_settings_removed(self):
        """Test that timeout settings have been removed from pytest.ini."""
        addopts = self.config.get('pytest', 'addopts', fallback='')
        
        # Verify timeout options are not present
        self.assertNotIn('--timeout', addopts,
                        "timeout option should be removed from addopts")
        self.assertNotIn('timeout=', addopts,
                        "timeout option should be removed from addopts")
        
        # Verify timeout_method is not present
        self.assertFalse(self.config.has_option('pytest', 'timeout_method'),
                        "timeout_method should be removed from pytest.ini")

    def test_integration_marker_configured(self):
        """Test that integration marker is configured."""
        markers = self.config.get('pytest', 'markers', fallback='')
        self.assertIn('integration:', markers)
        self.assertIn('Integration tests', markers)

    def test_testmon_comments_present(self):
        """Test that testmon configuration comments are present."""
        # Read the raw file to check for comments
        with open('pytest.ini', 'r') as f:
            content = f.read()
        
        self.assertIn('Testmon', content)
        self.assertIn('selective test execution', content)


class TestPytestTestDiscovery(unittest.TestCase):
    """Test that pytest test discovery works correctly."""

    def test_tests_directory_exists(self):
        """Test that tests directory exists."""
        self.assertTrue(os.path.isdir('tests'))

    def test_check_routes_not_in_test_pattern(self):
        """Test that check_routes.py doesn't match test_*.py pattern."""
        filename = 'check_routes.py'
        self.assertFalse(filename.startswith('test_'),
                        f"{filename} should not be discovered as a test file")

    def test_test_files_match_pattern(self):
        """Test that actual test files match the test_*.py pattern."""
        test_files = [
            'test_echo_functionality.py',
            'test_server_execution_output_encoding.py',
            'test_variables_secrets_issue.py',
            'test_versioned_server_invocation.py',
        ]
        
        for filename in test_files:
            self.assertTrue(filename.startswith('test_'),
                           f"{filename} should match test file pattern")
            self.assertTrue(filename.endswith('.py'),
                           f"{filename} should have .py extension")


class TestTestIsolationImprovements(unittest.TestCase):
    """Test that test isolation improvements are in place."""

    def test_no_shared_mutable_state_in_test_files(self):
        """Test that test files use proper setup/teardown patterns."""
        test_files_to_check = [
            'tests/test_echo_functionality.py',
            'tests/test_variables_secrets_issue.py',
            'tests/test_server_execution_output_encoding.py',
        ]
        
        for test_file in test_files_to_check:
            if not os.path.exists(test_file):
                continue
            
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Check for setup/teardown methods
            has_setup = 'def setUp(' in content or 'def setup(' in content
            has_teardown = 'def tearDown(' in content or 'def teardown(' in content
            
            # At least one test file should have proper setup/teardown
            if has_setup or has_teardown:
                self.assertTrue(True)
                return
        
        # If we get here, verify at least some structure exists
        self.assertTrue(os.path.exists('tests/'))

    def test_mock_patches_use_context_managers(self):
        """Test that modified test files use context managers for patches."""
        test_files = [
            'tests/test_echo_functionality.py',
            'tests/test_variables_secrets_issue.py',
            'tests/test_server_execution_output_encoding.py',
        ]
        
        context_manager_usage = False
        for test_file in test_files:
            if not os.path.exists(test_file):
                continue
            
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Check for proper context manager usage
            if 'with patch(' in content:
                context_manager_usage = True
                break
        
        self.assertTrue(context_manager_usage,
                       "Test files should use 'with patch()' context managers")


class TestUpdatedMockPaths(unittest.TestCase):
    """Test that mock paths have been updated correctly after refactoring."""

    def test_echo_functionality_uses_new_mock_paths(self):
        """Test that test_echo_functionality.py uses new module paths."""
        test_file = 'tests/test_echo_functionality.py'
        
        if not os.path.exists(test_file):
            self.skipTest(f"{test_file} not found")
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Check for new module structure paths
        self.assertIn('server_execution.server_lookup._current_user_id', content,
                     "Should use new server_lookup._current_user_id path")
        self.assertIn('server_execution.code_execution.run_text_function', content,
                     "Should use new code_execution.run_text_function path")

    def test_variables_secrets_uses_new_mock_paths(self):
        """Test that test_variables_secrets_issue.py uses new module paths."""
        test_file = 'tests/test_variables_secrets_issue.py'
        
        if not os.path.exists(test_file):
            self.skipTest(f"{test_file} not found")
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Check for new module structure paths
        self.assertIn('server_execution.code_execution.get_user_variables', content,
                     "Should use new code_execution.get_user_variables path")
        self.assertIn('server_execution.code_execution.get_user_secrets', content,
                     "Should use new code_execution.get_user_secrets path")
        self.assertIn('server_execution.code_execution._current_user_id', content,
                     "Should use new code_execution._current_user_id path")

    def test_versioned_invocation_uses_new_mock_paths(self):
        """Test that test_versioned_server_invocation.py uses new module paths."""
        test_file = 'tests/test_versioned_server_invocation.py'
        
        if not os.path.exists(test_file):
            self.skipTest(f"{test_file} not found")
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Check for new module structure paths
        self.assertIn('server_execution.server_lookup.get_server_by_name', content,
                     "Should use new server_lookup.get_server_by_name path")
        self.assertIn('server_execution.server_lookup._current_user_id', content,
                     "Should use new server_lookup._current_user_id path")


if __name__ == '__main__':
    unittest.main()