"""Tests for the urleditor server."""

import pytest
from unittest.mock import Mock


# Import the server module by loading it as text and executing it
def load_urleditor_module():
    """Load the urleditor server module."""
    import sys
    from pathlib import Path
    
    # Read the urleditor.py file
    urleditor_path = Path(__file__).parent.parent / "reference_templates" / "servers" / "definitions" / "urleditor.py"
    with open(urleditor_path, 'r') as f:
        code = f.read()
    
    # Create a module namespace
    module_namespace = {}
    
    # Execute the code in the namespace
    exec(code, module_namespace)
    
    return module_namespace


class TestURLEditorServerBasics:
    """Test basic functionality of the urleditor server."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.module = load_urleditor_module()
    
    def test_main_function_exists(self):
        """Test that the main function exists."""
        assert 'main' in self.module
        assert callable(self.module['main'])
    
    def test_main_returns_html_by_default(self):
        """Test that main returns HTML content."""
        result = self.module['main']()
        
        assert isinstance(result, dict)
        assert 'output' in result
        assert 'content_type' in result
        assert result['content_type'] == 'text/html'
        assert '<!DOCTYPE html>' in result['output']
    
    def test_main_rejects_chained_input(self):
        """Test that the server rejects being used in a chain."""
        result = self.module['main'](input_data="some input from previous server")
        
        assert isinstance(result, dict)
        assert 'output' in result
        assert 'status' in result
        assert result['status'] == 400
        assert 'does not support URL chaining' in result['output']
    
    def test_main_accepts_none_input(self):
        """Test that the server works when input_data is None."""
        result = self.module['main'](input_data=None)
        
        assert isinstance(result, dict)
        assert 'output' in result
        assert result.get('content_type') == 'text/html'
        assert result.get('status', 200) != 400


class TestURLEditorHelperFunctions:
    """Test helper functions in the urleditor server."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.module = load_urleditor_module()
    
    def test_parse_url_from_input_handles_empty(self):
        """Test that _parse_url_from_input handles empty input."""
        parse_func = self.module['_parse_url_from_input']
        
        result = parse_func("")
        assert result == ""
    
    def test_parse_url_from_input_adds_leading_slash(self):
        """Test that _parse_url_from_input adds leading slash."""
        parse_func = self.module['_parse_url_from_input']
        
        result = parse_func("echo/test")
        assert result == "/echo/test"
    
    def test_parse_url_from_input_strips_whitespace(self):
        """Test that _parse_url_from_input strips whitespace."""
        parse_func = self.module['_parse_url_from_input']
        
        result = parse_func("  /echo/test  ")
        assert result == "/echo/test"
    
    def test_should_redirect_returns_false_for_root(self):
        """Test that _should_redirect returns False for root path."""
        redirect_func = self.module['_should_redirect']
        
        should_redirect, redirect_url = redirect_func("/")
        assert should_redirect is False
        assert redirect_url is None
    
    def test_should_redirect_returns_false_for_empty(self):
        """Test that _should_redirect returns False for empty path."""
        redirect_func = self.module['_should_redirect']
        
        should_redirect, redirect_url = redirect_func("")
        assert should_redirect is False
        assert redirect_url is None
    
    def test_should_redirect_returns_true_for_subpath(self):
        """Test that _should_redirect returns True for subpath."""
        redirect_func = self.module['_should_redirect']
        
        should_redirect, redirect_url = redirect_func("/echo/test")
        assert should_redirect is True
        assert redirect_url == "/urleditor#/echo/test"
    
    def test_get_html_page_returns_html(self):
        """Test that _get_html_page returns HTML."""
        html_func = self.module['_get_html_page']
        
        html = html_func("")
        assert '<!DOCTYPE html>' in html
        assert '<title>URL Editor</title>' in html
    
    def test_get_html_page_includes_ace_editor(self):
        """Test that _get_html_page includes Ace editor."""
        html_func = self.module['_get_html_page']
        
        html = html_func("")
        assert 'ace.edit' in html
        assert 'url-editor' in html
    
    def test_get_html_page_escapes_initial_url(self):
        """Test that _get_html_page escapes the initial URL."""
        html_func = self.module['_get_html_page']
        
        html = html_func("<script>alert('xss')</script>")
        # Should be HTML-escaped
        assert "&lt;script&gt;" in html or "<script>alert('xss')</script>" not in html


class TestURLEditorWithRequest:
    """Test urleditor with mock request objects."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.module = load_urleditor_module()
    
    def test_main_with_urleditor_path(self):
        """Test main with request path /urleditor."""
        request = Mock()
        request.path = "/urleditor"
        
        result = self.module['main'](request=request)
        
        assert isinstance(result, dict)
        assert 'output' in result
        assert result['content_type'] == 'text/html'
    
    def test_main_with_subpath_redirects(self):
        """Test main with request path /urleditor/echo redirects."""
        request = Mock()
        request.path = "/urleditor/echo"
        
        result = self.module['main'](request=request)
        
        assert isinstance(result, dict)
        assert 'redirect' in result
        assert result['redirect'] == "/urleditor#/echo"
        assert result.get('status') == 302
    
    def test_main_with_complex_subpath_redirects(self):
        """Test main with complex subpath redirects correctly."""
        request = Mock()
        request.path = "/urleditor/markdown/echo/test"
        
        result = self.module['main'](request=request)
        
        assert isinstance(result, dict)
        assert 'redirect' in result
        assert result['redirect'] == "/urleditor#/markdown/echo/test"
