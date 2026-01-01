"""Unit tests for the HRX gateway response transform."""

from __future__ import annotations

from unittest.mock import MagicMock

from reference_templates.gateways.transforms.hrx_response import (
    _build_breadcrumb,
    _fix_css_urls,
    _fix_relative_urls,
    transform_response,
)


def test_fix_relative_urls_handles_absolute_paths():
    """Test that absolute paths in archive are fixed correctly."""
    html = '<a href="/docs/index.html">Docs</a>'
    archive_cid = "ABC123"
    file_path = "readme.html"
    
    result = _fix_relative_urls(html, archive_cid, file_path)
    
    assert f'/gateway/hrx/{archive_cid}/docs/index.html' in result


def test_fix_relative_urls_handles_relative_paths():
    """Test that relative paths are fixed correctly."""
    html = '<a href="other.html">Other</a>'
    archive_cid = "ABC123"
    file_path = "readme.html"
    
    result = _fix_relative_urls(html, archive_cid, file_path)
    
    assert f'/gateway/hrx/{archive_cid}/other.html' in result


def test_fix_relative_urls_skips_external_urls():
    """Test that external URLs are not modified."""
    html = '<a href="https://example.com">Example</a>'
    archive_cid = "ABC123"
    file_path = "readme.html"
    
    result = _fix_relative_urls(html, archive_cid, file_path)
    
    assert 'https://example.com' in result
    assert '/gateway/hrx/' not in result


def test_fix_relative_urls_handles_nested_files():
    """Test that relative URLs from nested files are fixed correctly."""
    html = '<a href="../index.html">Up</a><a href="sub/page.html">Down</a>'
    archive_cid = "ABC123"
    file_path = "docs/readme.html"
    
    result = _fix_relative_urls(html, archive_cid, file_path)
    
    # Base path for docs/readme.html is /gateway/hrx/ABC123/docs
    assert f'/gateway/hrx/{archive_cid}/docs/../index.html' in result
    assert f'/gateway/hrx/{archive_cid}/docs/sub/page.html' in result


def test_fix_css_urls_handles_relative_paths():
    """Test that CSS url() references are fixed."""
    css = 'background: url("../images/bg.png");'
    archive_cid = "ABC123"
    file_path = "css/style.css"
    
    result = _fix_css_urls(css, archive_cid, file_path)
    
    assert f'/gateway/hrx/{archive_cid}/css/../images/bg.png' in result


def test_fix_css_urls_skips_external_urls():
    """Test that external URLs in CSS are not modified."""
    css = 'background: url("https://example.com/bg.png");'
    archive_cid = "ABC123"
    file_path = "style.css"
    
    result = _fix_css_urls(css, archive_cid, file_path)
    
    assert 'https://example.com/bg.png' in result
    assert '/gateway/hrx/' not in result


def test_build_breadcrumb_root():
    """Test breadcrumb for archive root."""
    archive_cid = "ABC123"
    current_path = ""
    
    result = _build_breadcrumb(archive_cid, current_path)
    
    assert f'/gateway/hrx/{archive_cid}' in result
    assert 'archive' in result


def test_build_breadcrumb_nested_path():
    """Test breadcrumb for nested path."""
    archive_cid = "ABC123"
    current_path = "docs/api/reference.html"
    
    result = _build_breadcrumb(archive_cid, current_path)
    
    assert 'archive' in result
    assert 'docs' in result
    assert 'api' in result
    assert 'reference.html' in result


def test_transform_response_uses_templates_for_error():
    """Test that error pages use external templates."""
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Error Page</html>"
    mock_resolve = MagicMock(return_value=mock_template)
    
    response_details = {
        "request_path": "/ABC123/nonexistent.txt",
        "status_code": 404,
        "text": "File not found",
        "headers": {},
    }
    context = {"resolve_template": mock_resolve}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/html"
    assert "Error Page" in result["output"]
    mock_resolve.assert_called_with("hrx_error.html")
    mock_template.render.assert_called_once()


def test_transform_response_uses_templates_for_directory():
    """Test that directory listings use external templates."""
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Directory</html>"
    mock_resolve = MagicMock(return_value=mock_template)
    
    response_details = {
        "request_path": "/ABC123/",
        "status_code": 200,
        "text": "file1.txt\nfile2.txt",
        "headers": {},
    }
    context = {"resolve_template": mock_resolve}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/html"
    assert "Directory" in result["output"]
    mock_resolve.assert_called_with("hrx_directory.html")
    mock_template.render.assert_called_once()


def test_transform_response_uses_templates_for_markdown():
    """Test that markdown files use external templates."""
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Markdown</html>"
    mock_resolve = MagicMock(return_value=mock_template)
    
    response_details = {
        "request_path": "/ABC123/README.md",
        "status_code": 200,
        "text": "# Hello World\n\nThis is a test.",
        "headers": {},
    }
    context = {"resolve_template": mock_resolve}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/html"
    assert "Markdown" in result["output"]
    mock_resolve.assert_called_with("hrx_markdown.html")
    mock_template.render.assert_called_once()


def test_transform_response_uses_templates_for_text():
    """Test that text files use external templates."""
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Text File</html>"
    mock_resolve = MagicMock(return_value=mock_template)
    
    response_details = {
        "request_path": "/ABC123/test.py",
        "status_code": 200,
        "text": "print('hello')",
        "headers": {"Content-Type": "text/plain"},
    }
    context = {"resolve_template": mock_resolve}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/html"
    assert "Text File" in result["output"]
    mock_resolve.assert_called_with("hrx_text.html")
    mock_template.render.assert_called_once()


def test_transform_response_requires_templates():
    """Test that transform raises error if templates not configured."""
    response_details = {
        "request_path": "/ABC123/nonexistent.txt",
        "status_code": 404,
        "text": "File not found",
        "headers": {},
    }
    context = {}  # No resolve_template
    
    try:
        transform_response(response_details, context)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "resolve_template not available" in str(e)


def test_transform_response_passes_through_css():
    """Test that CSS files are passed through with URL fixing."""
    response_details = {
        "request_path": "/ABC123/style.css",
        "status_code": 200,
        "text": 'body { background: url("bg.png"); }',
        "headers": {"Content-Type": "text/css"},
    }
    context = {"resolve_template": MagicMock()}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/css"
    assert "/gateway/hrx/ABC123/bg.png" in result["output"]


def test_transform_response_fixes_html_urls():
    """Test that HTML files have relative URLs fixed."""
    response_details = {
        "request_path": "/ABC123/index.html",
        "status_code": 200,
        "text": '<a href="about.html">About</a>',
        "headers": {"Content-Type": "text/html"},
    }
    context = {"resolve_template": MagicMock()}
    
    result = transform_response(response_details, context)
    
    assert result["content_type"] == "text/html"
    assert "/gateway/hrx/ABC123/about.html" in result["output"]
