"""Tests for validate_github_pages.py script."""

import importlib.util
import sys
from pathlib import Path


def _load_validate_module():
    module_name = "test_validate_github_pages"
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "validate_github_pages.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load validate_github_pages module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


validate = _load_validate_module()


def test_extract_git_sha_finds_valid_sha() -> None:
    """Test that extract_git_sha finds a valid 40-character SHA."""
    html_content = """
    <html>
    <body>
      <h1>Test Page</h1>
      <div class="git-sha" data-git-sha="1234567890abcdef1234567890abcdef12345678" style="display: none;">1234567890abcdef1234567890abcdef12345678</div>
      <p>Content</p>
    </body>
    </html>
    """
    result = validate.extract_git_sha(html_content)
    assert result == "1234567890abcdef1234567890abcdef12345678"


def test_extract_git_sha_returns_none_for_missing_sha() -> None:
    """Test that extract_git_sha returns None when SHA is not present."""
    html_content = """
    <html>
    <body>
      <h1>Test Page</h1>
      <p>No SHA here</p>
    </body>
    </html>
    """
    result = validate.extract_git_sha(html_content)
    assert result is None


def test_extract_git_sha_returns_none_for_short_sha() -> None:
    """Test that extract_git_sha returns None for SHAs shorter than 40 chars."""
    html_content = """
    <html>
    <body>
      <div class="git-sha" data-git-sha="abc123" style="display: none;">abc123</div>
    </body>
    </html>
    """
    result = validate.extract_git_sha(html_content)
    assert result is None


def test_extract_git_sha_returns_none_for_invalid_chars() -> None:
    """Test that extract_git_sha returns None for SHAs with non-hex characters."""
    html_content = """
    <html>
    <body>
      <div class="git-sha" data-git-sha="g234567890abcdef1234567890abcdef12345678" style="display: none;">invalid</div>
    </body>
    </html>
    """
    result = validate.extract_git_sha(html_content)
    assert result is None


def test_validation_result_creation() -> None:
    """Test that ValidationResult can be created with correct fields."""
    result = validate.ValidationResult(
        name="Test Check",
        success=True,
        message="✓ Test passed",
    )
    assert result.name == "Test Check"
    assert result.success is True
    assert result.message == "✓ Test passed"
