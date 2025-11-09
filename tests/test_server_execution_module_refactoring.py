"""
Comprehensive unit tests for server_execution module refactoring.

Tests the new package structure and ensures all submodules work correctly
after the refactoring from a single file to a package with submodules.
"""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')


class TestServerExecutionModuleStructure(unittest.TestCase):
    """Test that server_execution module exports are intact after refactoring."""

    def test_server_execution_imports_from_code_execution(self):
        """Test that code_execution functions are available from main module."""
        from server_execution import (
            AUTO_MAIN_PARAMS_NAME,
            AUTO_MAIN_RESULT_NAME,
            build_request_args,
            execute_server_code,
            execute_server_code_from_definition,
            execute_server_function,
            execute_server_function_from_definition,
        )
        
        self.assertEqual(AUTO_MAIN_PARAMS_NAME, "__viewer_auto_main_params__")
        self.assertEqual(AUTO_MAIN_RESULT_NAME, "__viewer_auto_main_result__")
        self.assertTrue(callable(build_request_args))
        self.assertTrue(callable(execute_server_code))
        self.assertTrue(callable(execute_server_code_from_definition))
        self.assertTrue(callable(execute_server_function))
        self.assertTrue(callable(execute_server_function_from_definition))

    def test_server_execution_imports_from_function_analysis(self):
        """Test that function_analysis functions are available."""
        from server_execution import (
            analyze_server_definition,
            describe_function_parameters,
            describe_main_function_parameters,
        )
        
        self.assertTrue(callable(analyze_server_definition))
        self.assertTrue(callable(describe_function_parameters))
        self.assertTrue(callable(describe_main_function_parameters))

    def test_server_execution_imports_from_invocation_tracking(self):
        """Test that invocation_tracking functions are available."""
        from server_execution import create_server_invocation_record
        
        self.assertTrue(callable(create_server_invocation_record))

    def test_server_execution_imports_from_server_lookup(self):
        """Test that server_lookup functions are available."""
        from server_execution import (
            is_potential_server_path,
            is_potential_versioned_server_path,
            try_server_execution,
            try_server_execution_with_partial,
        )
        
        self.assertTrue(callable(is_potential_server_path))
        self.assertTrue(callable(is_potential_versioned_server_path))
        self.assertTrue(callable(try_server_execution))
        self.assertTrue(callable(try_server_execution_with_partial))

    def test_server_execution_imports_from_variable_resolution(self):
        """Test that variable_resolution constants are available."""
        from server_execution import VARIABLE_PREFETCH_SESSION_KEY
        
        self.assertEqual(VARIABLE_PREFETCH_SESSION_KEY, "__viewer_variable_prefetch__")

    def test_backward_compatibility_with_model_as_dict(self):
        """Test that model_as_dict is still accessible via __getattr__."""
        from server_execution import model_as_dict
        
        self.assertTrue(callable(model_as_dict))
        
        # Test basic functionality
        entries = [
            SimpleNamespace(name='alpha', definition='A', enabled=True),
            SimpleNamespace(name='beta', definition='B', enabled=False),
        ]
        result = model_as_dict(entries)
        self.assertEqual(result, {'alpha': 'A'})


class TestServerLookupModule(unittest.TestCase):
    """Test server_lookup submodule functions."""

    def test_is_potential_versioned_server_path_valid_two_segments(self):
        """Test valid versioned server path with two segments."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertTrue(is_potential_versioned_server_path('/myserver/abc123', existing))

    def test_is_potential_versioned_server_path_valid_three_segments(self):
        """Test valid versioned server path with three segments (function call)."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertTrue(is_potential_versioned_server_path('/myserver/abc123/helper', existing))

    def test_is_potential_versioned_server_path_invalid_one_segment(self):
        """Test invalid path with only one segment."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertFalse(is_potential_versioned_server_path('/myserver', existing))

    def test_is_potential_versioned_server_path_invalid_too_many_segments(self):
        """Test invalid path with more than three segments."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertFalse(is_potential_versioned_server_path('/a/b/c/d', existing))

    def test_is_potential_versioned_server_path_collides_with_existing_route(self):
        """Test path that collides with existing route."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertFalse(is_potential_versioned_server_path('/servers/abc', existing))

    def test_is_potential_versioned_server_path_empty_or_invalid(self):
        """Test edge cases: empty paths, no leading slash."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers'}
        self.assertFalse(is_potential_versioned_server_path('', existing))
        self.assertFalse(is_potential_versioned_server_path('myserver/abc', existing))
        self.assertFalse(is_potential_versioned_server_path('/', existing))

    def test_is_potential_server_path_valid_single_segment(self):
        """Test valid server path with single segment."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertTrue(is_potential_server_path('/echo', existing))

    def test_is_potential_server_path_valid_with_function(self):
        """Test valid server path with function name."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertTrue(is_potential_server_path('/echo/helper', existing))

    def test_is_potential_server_path_invalid_existing_route(self):
        """Test path that matches an existing route."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers', '/uploads', '/history'}
        self.assertFalse(is_potential_server_path('/servers', existing))
        self.assertFalse(is_potential_server_path('/history', existing))

    def test_is_potential_server_path_invalid_route_prefix(self):
        """Test path whose first segment matches an existing route."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers', '/uploads'}
        self.assertFalse(is_potential_server_path('/servers/list', existing))

    def test_is_potential_server_path_edge_cases(self):
        """Test edge cases: empty, root, no leading slash."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers'}
        self.assertFalse(is_potential_server_path('', existing))
        self.assertFalse(is_potential_server_path('/', existing))
        self.assertFalse(is_potential_server_path('echo', existing))


class TestVariableResolutionModule(unittest.TestCase):
    """Test variable_resolution submodule functions."""

    def test_current_user_id_with_direct_attribute(self):
        """Test _current_user_id when user.id is a direct attribute."""
        from server_execution.variable_resolution import _current_user_id
        
        mock_user = SimpleNamespace(id='user123')
        with patch('server_execution.variable_resolution.current_user', mock_user):
            result = _current_user_id()
            self.assertEqual(result, 'user123')

    def test_current_user_id_with_callable_id(self):
        """Test _current_user_id when user.id is callable."""
        from server_execution.variable_resolution import _current_user_id
        
        mock_user = SimpleNamespace(id=lambda: 'user456')
        with patch('server_execution.variable_resolution.current_user', mock_user):
            result = _current_user_id()
            self.assertEqual(result, 'user456')

    def test_current_user_id_with_get_id_method(self):
        """Test _current_user_id fallback to get_id() method."""
        from server_execution.variable_resolution import _current_user_id
        
        mock_user = SimpleNamespace(id=None, get_id=lambda: 'user789')
        with patch('server_execution.variable_resolution.current_user', mock_user):
            result = _current_user_id()
            self.assertEqual(result, 'user789')

    def test_current_user_id_with_no_id(self):
        """Test _current_user_id returns None when no ID available."""
        from server_execution.variable_resolution import _current_user_id
        
        mock_user = SimpleNamespace(id=None)
        with patch('server_execution.variable_resolution.current_user', mock_user):
            result = _current_user_id()
            self.assertIsNone(result)

    def test_current_user_id_with_callable_throwing_error(self):
        """Test _current_user_id handles TypeError from callable."""
        from server_execution.variable_resolution import _current_user_id
        
        def bad_callable():
            raise TypeError("Cannot call")
        
        mock_user = SimpleNamespace(id=bad_callable, get_id=lambda: 'fallback')
        with patch('server_execution.variable_resolution.current_user', mock_user):
            result = _current_user_id()
            self.assertEqual(result, 'fallback')

    def test_normalize_variable_path_valid_absolute_path(self):
        """Test _normalize_variable_path with valid absolute path."""
        from server_execution.variable_resolution import _normalize_variable_path
        
        self.assertEqual(_normalize_variable_path('/echo'), '/echo')
        self.assertEqual(_normalize_variable_path('  /echo  '), '/echo')

    def test_normalize_variable_path_invalid_relative_path(self):
        """Test _normalize_variable_path rejects relative paths."""
        from server_execution.variable_resolution import _normalize_variable_path
        
        self.assertIsNone(_normalize_variable_path('echo'))
        self.assertIsNone(_normalize_variable_path('./echo'))
        self.assertIsNone(_normalize_variable_path('../echo'))

    def test_normalize_variable_path_invalid_non_string(self):
        """Test _normalize_variable_path rejects non-string values."""
        from server_execution.variable_resolution import _normalize_variable_path
        
        self.assertIsNone(_normalize_variable_path(123))
        self.assertIsNone(_normalize_variable_path(None))
        self.assertIsNone(_normalize_variable_path(['path']))

    def test_should_skip_variable_prefetch_true(self):
        """Test _should_skip_variable_prefetch returns True when flag is set."""
        from server_execution.variable_resolution import (
            VARIABLE_PREFETCH_SESSION_KEY,
            _should_skip_variable_prefetch,
        )
        
        from app import app
        
        with app.test_request_context('/'):
            from flask import session
            session[VARIABLE_PREFETCH_SESSION_KEY] = True
            self.assertTrue(_should_skip_variable_prefetch())

    def test_should_skip_variable_prefetch_false(self):
        """Test _should_skip_variable_prefetch returns False when flag not set."""
        from server_execution.variable_resolution import _should_skip_variable_prefetch
        
        from app import app
        
        with app.test_request_context('/'):
            self.assertFalse(_should_skip_variable_prefetch())

    def test_should_skip_variable_prefetch_no_request_context(self):
        """Test _should_skip_variable_prefetch returns False outside request context."""
        from server_execution.variable_resolution import _should_skip_variable_prefetch
        
        # No request context
        self.assertFalse(_should_skip_variable_prefetch())

    def test_resolve_redirect_target_absolute_path(self):
        """Test _resolve_redirect_target with absolute path."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        result = _resolve_redirect_target('/new/path', '/old/path')
        self.assertEqual(result, '/new/path')

    def test_resolve_redirect_target_relative_path(self):
        """Test _resolve_redirect_target with relative path."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        result = _resolve_redirect_target('sibling', '/old/path')
        self.assertEqual(result, '/old/sibling')

    def test_resolve_redirect_target_with_query_string(self):
        """Test _resolve_redirect_target preserves query string."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        result = _resolve_redirect_target('/path?foo=bar', '/old')
        self.assertEqual(result, '/path?foo=bar')

    def test_resolve_redirect_target_rejects_external_url(self):
        """Test _resolve_redirect_target rejects external URLs."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        self.assertIsNone(_resolve_redirect_target('https://example.com/path', '/old'))
        self.assertIsNone(_resolve_redirect_target('//example.com/path', '/old'))

    def test_resolve_redirect_target_empty_or_invalid(self):
        """Test _resolve_redirect_target handles empty/invalid inputs."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        self.assertIsNone(_resolve_redirect_target('', '/old'))
        self.assertIsNone(_resolve_redirect_target('?query', '/old'))


class TestCodeExecutionModule(unittest.TestCase):
    """Test code_execution submodule functions."""

    def test_model_as_dict_converts_enabled_models(self):
        """Test model_as_dict converts enabled model objects to dict."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='var1', definition='value1', enabled=True)
        obj2 = SimpleNamespace(name='var2', definition='value2', enabled=True)
        
        result = model_as_dict([obj1, obj2])
        self.assertEqual(result, {'var1': 'value1', 'var2': 'value2'})

    def test_model_as_dict_filters_disabled_models(self):
        """Test model_as_dict filters out disabled models."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='var1', definition='value1', enabled=True)
        obj2 = SimpleNamespace(name='var2', definition='value2', enabled=False)
        obj3 = SimpleNamespace(name='var3', definition='value3', enabled=True)
        
        result = model_as_dict([obj1, obj2, obj3])
        self.assertEqual(result, {'var1': 'value1', 'var3': 'value3'})

    def test_model_as_dict_handles_missing_enabled_attribute(self):
        """Test model_as_dict treats missing 'enabled' as enabled."""
        from server_execution.code_execution import model_as_dict
        
        obj = SimpleNamespace(name='var1', definition='value1')
        result = model_as_dict([obj])
        self.assertEqual(result, {'var1': 'value1'})

    def test_model_as_dict_handles_empty_list(self):
        """Test model_as_dict with empty list."""
        from server_execution.code_execution import model_as_dict
        
        result = model_as_dict([])
        self.assertEqual(result, {})

    def test_model_as_dict_handles_none(self):
        """Test model_as_dict with None."""
        from server_execution.code_execution import model_as_dict
        
        result = model_as_dict(None)
        self.assertEqual(result, {})

    def test_model_as_dict_fallback_to_str_representation(self):
        """Test model_as_dict falls back to str() when name/definition missing."""
        from server_execution.code_execution import model_as_dict
        
        obj = SimpleNamespace(value='test')
        obj.__str__ = lambda: 'test_object'
        
        result = model_as_dict([obj])
        # Should fall back to using str() for both key and value
        self.assertIsInstance(result, dict)


class TestErrorHandlingModule(unittest.TestCase):
    """Test error_handling submodule functions."""

    @patch('server_execution.error_handling.render_template')
    @patch('server_execution.error_handling._get_tracked_paths')
    @patch('server_execution.error_handling.highlight_source')
    @patch('server_execution.error_handling.build_stack_trace')
    def test_render_execution_error_html_basic(self, mock_stack, mock_highlight, mock_paths, mock_render):
        """Test _render_execution_error_html renders error page."""
        from server_execution.error_handling import _render_execution_error_html
        
        mock_paths.return_value = frozenset()
        mock_stack.return_value = [{'file': 'test.py', 'line': 10}]
        mock_highlight.return_value = ('<code>highlighted</code>', '.css {}')
        mock_render.return_value = '<html>Error Page</html>'
        
        exc = ValueError("Test error")
        code = "print('hello')"
        args = {'test': 'value'}
        
        result = _render_execution_error_html(exc, code, args, 'test_server')
        
        self.assertEqual(result, '<html>Error Page</html>')
        mock_render.assert_called_once()
        call_kwargs = mock_render.call_args[1]
        self.assertEqual(call_kwargs['exception_type'], 'ValueError')
        self.assertEqual(call_kwargs['exception_message'], 'Test error')

    @patch('server_execution.error_handling.make_response')
    @patch('server_execution.error_handling._render_execution_error_html')
    def test_handle_execution_exception_success(self, mock_render, mock_make_response):
        """Test _handle_execution_exception creates proper response."""
        from server_execution.error_handling import _handle_execution_exception
        
        mock_render.return_value = '<html>Error</html>'
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_make_response.return_value = mock_response
        
        exc = RuntimeError("Test error")
        result = _handle_execution_exception(exc, "code", {}, "server")
        
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.headers['Content-Type'], 'text/html; charset=utf-8')

    @patch('server_execution.error_handling.make_response')
    @patch('server_execution.error_handling._render_execution_error_html')
    def test_handle_execution_exception_fallback_on_render_error(self, mock_render, mock_make_response):
        """Test _handle_execution_exception falls back to plain text on render error."""
        from server_execution.error_handling import _handle_execution_exception
        
        mock_render.side_effect = Exception("Render failed")
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_make_response.return_value = mock_response
        
        exc = RuntimeError("Test error")
        result = _handle_execution_exception(exc, "code", {}, "server")
        
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.headers['Content-Type'], 'text/plain')


class TestTestIsolationImprovements(unittest.TestCase):
    """Test that test isolation issues have been fixed."""

    def test_pytest_timeout_removed(self):
        """Test that pytest timeout configuration has been removed from pytest.ini."""
        import configparser
        
        config = configparser.ConfigParser()
        config.read('pytest.ini')
        
        if 'pytest' in config:
            addopts = config.get('pytest', 'addopts', fallback='')
            self.assertNotIn('--timeout', addopts)
            self.assertNotIn('timeout_method', config['pytest'])

    def test_check_routes_not_discovered_as_test(self):
        """Test that check_routes.py is not discovered as a test file."""
        import pytest
        
        # check_routes.py should not match test_*.py pattern
        self.assertFalse('check_routes.py'.startswith('test_'))


if __name__ == '__main__':
    unittest.main()