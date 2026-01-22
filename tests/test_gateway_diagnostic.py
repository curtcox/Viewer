"""Tests for gateway_lib.rendering.diagnostic module."""

from definitions.gateway_lib.rendering.diagnostic import (
    format_exception_summary,
    derive_exception_summary_from_traceback,
    extract_exception_summary_from_internal_error_html,
    extract_stack_trace_list_from_internal_error_html,
    safe_preview_request_details,
    format_exception_detail,
)


class TestFormatExceptionSummary:
    """Tests for format_exception_summary function."""
    
    def test_format_exception_with_message(self):
        """Test formatting exception with message."""
        exc = ValueError("Invalid value")
        result = format_exception_summary(exc)
        assert result == "ValueError: Invalid value"
    
    def test_format_exception_without_message(self):
        """Test formatting exception without message."""
        exc = ValueError()
        result = format_exception_summary(exc)
        assert result == "ValueError"
    
    def test_format_custom_exception(self):
        """Test formatting custom exception."""
        class CustomError(Exception):
            pass
        
        exc = CustomError("Custom message")
        result = format_exception_summary(exc)
        assert result == "CustomError: Custom message"


class TestDeriveExceptionSummaryFromTraceback:
    """Tests for derive_exception_summary_from_traceback function."""
    
    def test_derive_from_valid_traceback(self):
        """Test deriving exception from valid traceback."""
        traceback = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    foo()
  File "test.py", line 5, in foo
    raise ValueError("test error")
ValueError: test error"""
        
        result = derive_exception_summary_from_traceback(traceback)
        assert result == "ValueError: test error"
    
    def test_derive_from_empty_traceback(self):
        """Test with empty traceback."""
        result = derive_exception_summary_from_traceback("")
        assert result is None
    
    def test_derive_from_none(self):
        """Test with None input."""
        result = derive_exception_summary_from_traceback(None)
        assert result is None
    
    def test_derive_from_whitespace_only(self):
        """Test with whitespace-only traceback."""
        result = derive_exception_summary_from_traceback("   \n\n  ")
        assert result is None
    
    def test_derive_from_traceback_without_colon(self):
        """Test with traceback without colon in last line."""
        traceback = """Some error
No colon here"""
        result = derive_exception_summary_from_traceback(traceback)
        assert result is None


class TestExtractExceptionSummaryFromInternalErrorHtml:
    """Tests for extract_exception_summary_from_internal_error_html function."""
    
    def test_extract_from_valid_html(self):
        """Test extracting from valid error HTML."""
        html = """<html>
<body>
<p><strong>Exception:</strong> ValueError: Invalid input</p>
</body>
</html>"""
        
        result = extract_exception_summary_from_internal_error_html(html)
        assert result == "ValueError: Invalid input"
    
    def test_extract_from_html_with_no_match(self):
        """Test with HTML without exception marker."""
        html = "<html><body>Some error</body></html>"
        result = extract_exception_summary_from_internal_error_html(html)
        assert result is None
    
    def test_extract_from_empty_html(self):
        """Test with empty HTML."""
        result = extract_exception_summary_from_internal_error_html("")
        assert result is None
    
    def test_extract_from_none(self):
        """Test with None input."""
        result = extract_exception_summary_from_internal_error_html(None)
        assert result is None


class TestExtractStackTraceListFromInternalErrorHtml:
    """Tests for extract_stack_trace_list_from_internal_error_html function."""
    
    def test_extract_stack_trace(self):
        """Test extracting stack trace from error HTML."""
        html = """<html>
<body>
<p><strong>Exception:</strong> ValueError: Invalid input</p>
<ol class="traceback">
<li>File "test.py", line 10</li>
<li>File "foo.py", line 5</li>
</ol>
</body>
</html>"""
        
        result = extract_stack_trace_list_from_internal_error_html(html)
        assert result is not None
        assert "ValueError: Invalid input" in result
        assert "<ol" in result
        assert "Stack trace" in result
    
    def test_extract_with_no_ol_tag(self):
        """Test with HTML without ol tag."""
        html = '<html><body><p><strong>Exception:</strong> Error</p></body></html>'
        result = extract_stack_trace_list_from_internal_error_html(html)
        assert result is None
    
    def test_extract_from_none(self):
        """Test with None input."""
        result = extract_stack_trace_list_from_internal_error_html(None)
        assert result is None


class TestSafePreviewRequestDetails:
    """Tests for safe_preview_request_details function."""
    
    def test_removes_authorization_header(self):
        """Test that authorization headers are removed."""
        details = {
            "path": "/test",
            "headers": {
                "Authorization": "Bearer secret-token",
                "Content-Type": "application/json",
            }
        }
        
        result = safe_preview_request_details(details)
        assert "Authorization" not in result["headers"]
        assert "Content-Type" in result["headers"]
    
    def test_removes_cookie_header(self):
        """Test that cookie headers are removed."""
        details = {
            "path": "/test",
            "headers": {
                "Cookie": "session=secret",
                "Content-Type": "text/html",
            }
        }
        
        result = safe_preview_request_details(details)
        assert "Cookie" not in result["headers"]
        assert "Content-Type" in result["headers"]
    
    def test_handles_lowercase_headers(self):
        """Test that lowercase header names are also removed."""
        details = {
            "path": "/test",
            "headers": {
                "authorization": "Bearer secret",
                "cookie": "session=secret",
            }
        }
        
        result = safe_preview_request_details(details)
        assert "authorization" not in result["headers"]
        assert "cookie" not in result["headers"]
    
    def test_preserves_other_fields(self):
        """Test that other fields are preserved."""
        details = {
            "path": "/test",
            "method": "POST",
            "headers": {"Authorization": "secret"},
            "json": {"data": "value"},
        }
        
        result = safe_preview_request_details(details)
        assert result["path"] == "/test"
        assert result["method"] == "POST"
        assert result["json"] == {"data": "value"}


class TestFormatExceptionDetail:
    """Tests for format_exception_detail function."""
    
    def test_format_with_exception(self):
        """Test formatting exception details."""
        exc = ValueError("Test error")
        result = format_exception_detail(exc)
        
        assert "ValueError: Test error" in result
        assert "Traceback:" in result
    
    def test_format_with_debug_context(self):
        """Test formatting with debug context."""
        exc = ValueError("Test error")
        debug_context = {
            "gateway": "test",
            "path": "/test/path",
        }
        
        result = format_exception_detail(exc, debug_context=debug_context)
        
        assert "ValueError: Test error" in result
        assert "Debug Context:" in result
        assert "gateway" in result
        assert "test" in result
