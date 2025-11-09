"""
Comprehensive edge case tests for server_execution module refactoring.

Tests edge cases, error conditions, and boundary scenarios for the refactored
server_execution package to ensure robustness.
"""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')


class TestVariableResolutionEdgeCases(unittest.TestCase):
    """Test edge cases in variable_resolution module."""

    def test_fetch_variable_content_prevents_infinite_recursion(self):
        """Test that _fetch_variable_content prevents infinite recursion."""
        from server_execution.variable_resolution import _fetch_variable_content
        from app import app
        
        with app.test_request_context('/echo'):
            # Should return None to prevent fetching current request path
            result = _fetch_variable_content('/echo')
            self.assertIsNone(result,
                            "Should prevent fetching current request path")

    def test_fetch_variable_content_without_app_context(self):
        """Test _fetch_variable_content returns None without app context."""
        from server_execution.variable_resolution import _fetch_variable_content
        
        # No app context
        result = _fetch_variable_content('/some/path')
        self.assertIsNone(result)

    def test_fetch_variable_content_without_user(self):
        """Test _fetch_variable_content returns None without user."""
        from server_execution.variable_resolution import _fetch_variable_content
        from app import app
        
        with app.app_context():
            with patch('server_execution.variable_resolution._current_user_id') as mock_user:
                mock_user.return_value = None
                result = _fetch_variable_content('/path')
                self.assertIsNone(result)

    def test_resolve_variable_values_with_empty_map(self):
        """Test _resolve_variable_values with empty variable map."""
        from server_execution.variable_resolution import _resolve_variable_values
        
        result = _resolve_variable_values({})
        self.assertEqual(result, {})

    def test_resolve_variable_values_with_none(self):
        """Test _resolve_variable_values with None input."""
        from server_execution.variable_resolution import _resolve_variable_values
        
        result = _resolve_variable_values(None)
        self.assertEqual(result, {})

    def test_resolve_variable_values_skips_prefetch_when_flagged(self):
        """Test _resolve_variable_values skips prefetch when flag is set."""
        from server_execution.variable_resolution import (
            VARIABLE_PREFETCH_SESSION_KEY,
            _resolve_variable_values,
        )
        from app import app
        
        with app.test_request_context('/'):
            from flask import session
            session[VARIABLE_PREFETCH_SESSION_KEY] = True
            
            variables = {'test': '/some/path'}
            result = _resolve_variable_values(variables)
            
            # Should return original values without fetching
            self.assertEqual(result['test'], '/some/path')

    def test_fetch_variable_via_client_with_redirect_loop(self):
        """Test _fetch_variable_via_client detects redirect loops."""
        from server_execution.variable_resolution import _fetch_variable_via_client
        from app import app
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {'Location': '/same/path'}
        mock_client.get.return_value = mock_response
        
        result = _fetch_variable_via_client(mock_client, '/same/path')
        self.assertIsNone(result, "Should detect redirect loops")

    def test_fetch_variable_via_client_with_non_200_status(self):
        """Test _fetch_variable_via_client handles non-200 status."""
        from server_execution.variable_resolution import _fetch_variable_via_client
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        
        result = _fetch_variable_via_client(mock_client, '/missing')
        self.assertIsNone(result)

    def test_fetch_variable_via_client_with_decode_error(self):
        """Test _fetch_variable_via_client handles decode errors."""
        from server_execution.variable_resolution import _fetch_variable_via_client
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.get_data.side_effect = UnicodeDecodeError(
            'utf-8', b'', 0, 1, 'invalid'
        )
        mock_client.get.return_value = mock_response
        
        result = _fetch_variable_via_client(mock_client, '/binary')
        self.assertIsNone(result)

    def test_resolve_redirect_target_with_relative_parent_path(self):
        """Test _resolve_redirect_target with ../ relative path."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        result = _resolve_redirect_target('../sibling', '/dir/current')
        self.assertEqual(result, '/dir/sibling')

    def test_resolve_redirect_target_with_fragment(self):
        """Test _resolve_redirect_target ignores fragments."""
        from server_execution.variable_resolution import _resolve_redirect_target
        
        result = _resolve_redirect_target('/path#section', '/old')
        # Fragment is not preserved in path
        self.assertTrue(result.startswith('/path'))


class TestCodeExecutionEdgeCases(unittest.TestCase):
    """Test edge cases in code_execution module."""

    def test_model_as_dict_with_objects_having_falsy_enabled(self):
        """Test model_as_dict with enabled=0 or enabled=False."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='var1', definition='val1', enabled=0)
        obj2 = SimpleNamespace(name='var2', definition='val2', enabled=False)
        obj3 = SimpleNamespace(name='var3', definition='val3', enabled='')
        
        result = model_as_dict([obj1, obj2, obj3])
        # All should be filtered out due to falsy enabled values
        self.assertEqual(result, {})

    def test_model_as_dict_with_mixed_enabled_types(self):
        """Test model_as_dict with various truthy enabled values."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='var1', definition='val1', enabled=True)
        obj2 = SimpleNamespace(name='var2', definition='val2', enabled=1)
        obj3 = SimpleNamespace(name='var3', definition='val3', enabled='yes')
        
        result = model_as_dict([obj1, obj2, obj3])
        self.assertEqual(len(result), 3)
        self.assertIn('var1', result)
        self.assertIn('var2', result)
        self.assertIn('var3', result)

    def test_model_as_dict_with_duplicate_names(self):
        """Test model_as_dict behavior with duplicate names."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='duplicate', definition='first', enabled=True)
        obj2 = SimpleNamespace(name='duplicate', definition='second', enabled=True)
        
        result = model_as_dict([obj1, obj2])
        # Later one should overwrite
        self.assertEqual(result['duplicate'], 'second')

    def test_model_as_dict_with_none_definition(self):
        """Test model_as_dict with None definition."""
        from server_execution.code_execution import model_as_dict
        
        obj = SimpleNamespace(name='var', definition=None, enabled=True)
        result = model_as_dict([obj])
        self.assertIn('var', result)
        self.assertIsNone(result['var'])

    def test_model_as_dict_with_complex_definition(self):
        """Test model_as_dict with complex definition types."""
        from server_execution.code_execution import model_as_dict
        
        obj1 = SimpleNamespace(name='dict_var', definition={'key': 'value'}, enabled=True)
        obj2 = SimpleNamespace(name='list_var', definition=[1, 2, 3], enabled=True)
        
        result = model_as_dict([obj1, obj2])
        self.assertEqual(result['dict_var'], {'key': 'value'})
        self.assertEqual(result['list_var'], [1, 2, 3])


class TestServerLookupEdgeCases(unittest.TestCase):
    """Test edge cases in server_lookup module."""

    @patch('server_execution.server_lookup.get_server_by_name')
    @patch('server_execution.server_lookup._current_user_id')
    def test_try_server_execution_with_disabled_server(self, mock_user_id, mock_get_server):
        """Test try_server_execution with disabled server."""
        from server_execution.server_lookup import try_server_execution
        
        mock_user_id.return_value = 'user123'
        mock_server = SimpleNamespace(name='test', definition='code', enabled=False)
        mock_get_server.return_value = mock_server
        
        result = try_server_execution('/test')
        self.assertIsNone(result, "Should return None for disabled server")

    @patch('server_execution.server_lookup._current_user_id')
    def test_try_server_execution_without_user(self, mock_user_id):
        """Test try_server_execution without authenticated user."""
        from server_execution.server_lookup import try_server_execution
        
        mock_user_id.return_value = None
        result = try_server_execution('/test')
        self.assertIsNone(result)

    def test_try_server_execution_with_empty_path(self):
        """Test try_server_execution with empty path."""
        from server_execution.server_lookup import try_server_execution
        
        result = try_server_execution('')
        self.assertIsNone(result)

    def test_try_server_execution_with_root_path(self):
        """Test try_server_execution with root path."""
        from server_execution.server_lookup import try_server_execution
        
        result = try_server_execution('/')
        self.assertIsNone(result)

    @patch('server_execution.server_lookup.get_server_by_name')
    @patch('server_execution.server_lookup._current_user_id')
    def test_try_server_execution_with_partial_disabled_server(self, mock_user_id, mock_get_server):
        """Test try_server_execution_with_partial with disabled server."""
        from server_execution.server_lookup import try_server_execution_with_partial
        
        mock_user_id.return_value = 'user123'
        mock_server = SimpleNamespace(name='test', enabled=False)
        mock_get_server.return_value = mock_server
        
        history_fetcher = Mock(return_value=[])
        result = try_server_execution_with_partial('/test/abc', history_fetcher)
        self.assertIsNone(result)

    def test_is_potential_versioned_server_path_with_unicode(self):
        """Test is_potential_versioned_server_path with unicode characters."""
        from server_execution.server_lookup import is_potential_versioned_server_path
        
        existing = {'/servers'}
        result = is_potential_versioned_server_path('/über/café', existing)
        self.assertTrue(result)

    def test_is_potential_server_path_with_special_chars(self):
        """Test is_potential_server_path with special characters."""
        from server_execution.server_lookup import is_potential_server_path
        
        existing = {'/servers'}
        # Paths with special chars should still be considered potential
        result = is_potential_server_path('/test-server', existing)
        self.assertTrue(result)


class TestErrorHandlingEdgeCases(unittest.TestCase):
    """Test edge cases in error_handling module."""

    @patch('server_execution.error_handling.make_response')
    @patch('server_execution.error_handling._render_execution_error_html')
    def test_handle_execution_exception_with_unicode_error(self, mock_render, mock_response):
        """Test _handle_execution_exception with unicode error message."""
        from server_execution.error_handling import _handle_execution_exception
        
        mock_render.return_value = '<html>Error: café</html>'
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_response.return_value = mock_resp
        
        exc = ValueError("Error with unicode: café ☕")
        result = _handle_execution_exception(exc, "code", {}, "server")
        
        self.assertEqual(result.status_code, 500)

    @patch('server_execution.error_handling.make_response')
    @patch('server_execution.error_handling._render_execution_error_html')
    def test_handle_execution_exception_with_empty_message(self, mock_render, mock_response):
        """Test _handle_execution_exception with empty error message."""
        from server_execution.error_handling import _handle_execution_exception
        
        mock_render.return_value = '<html>Error</html>'
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_response.return_value = mock_resp
        
        exc = ValueError("")
        result = _handle_execution_exception(exc, "code", {}, "server")
        
        self.assertEqual(result.status_code, 500)


if __name__ == '__main__':
    unittest.main()