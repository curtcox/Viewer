"""Tests for gateway_lib.cid.normalizer module."""

import pytest
from gateway_lib.cid.normalizer import normalize_cid_lookup, parse_hrx_gateway_args


class TestNormalizeCidLookup:
    """Tests for normalize_cid_lookup function."""
    
    def test_normalize_none_returns_none(self):
        """Test that None input returns None."""
        assert normalize_cid_lookup(None) is None
    
    def test_normalize_empty_string_returns_none(self):
        """Test that empty string returns None."""
        assert normalize_cid_lookup("") is None
    
    def test_normalize_whitespace_only_returns_none(self):
        """Test that whitespace-only string returns None."""
        assert normalize_cid_lookup("   ") is None
        assert normalize_cid_lookup("\n\t  ") is None
    
    def test_normalize_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = normalize_cid_lookup("  /test/path  ")
        assert result == "/test/path"
    
    def test_normalize_preserves_leading_slash(self):
        """Test that leading slash is preserved."""
        result = normalize_cid_lookup("/CID123")
        assert result == "/CID123"
    
    def test_normalize_path_without_slash(self):
        """Test normalization of path without leading slash."""
        result = normalize_cid_lookup("test/path")
        assert result == "test/path"


class TestParseHrxGatewayArgs:
    """Tests for parse_hrx_gateway_args function."""
    
    def test_parse_with_archive_and_path(self):
        """Test parsing path with archive and file path."""
        archive, file_path = parse_hrx_gateway_args("archive/file/path")
        assert archive == "archive"
        assert file_path == "file/path"
    
    def test_parse_with_archive_only(self):
        """Test parsing path with archive only."""
        archive, file_path = parse_hrx_gateway_args("archive")
        assert archive == "archive"
        assert file_path == ""
    
    def test_parse_with_empty_string(self):
        """Test parsing empty string."""
        archive, file_path = parse_hrx_gateway_args("")
        assert archive == ""
        assert file_path == ""
    
    def test_parse_with_none(self):
        """Test parsing None."""
        archive, file_path = parse_hrx_gateway_args(None)
        assert archive == ""
        assert file_path == ""
    
    def test_parse_with_leading_slash(self):
        """Test parsing path with leading slash."""
        archive, file_path = parse_hrx_gateway_args("/archive/file/path")
        assert archive == "archive"
        assert file_path == "file/path"
    
    def test_parse_with_trailing_slash(self):
        """Test parsing path with trailing slash (strips trailing slashes)."""
        archive, file_path = parse_hrx_gateway_args("archive/file/path/")
        assert archive == "archive"
        assert file_path == "file/path"  # Trailing slash is stripped
    
    def test_parse_with_multiple_slashes(self):
        """Test parsing path with multiple slashes."""
        archive, file_path = parse_hrx_gateway_args("archive/file/sub/path")
        assert archive == "archive"
        assert file_path == "file/sub/path"
