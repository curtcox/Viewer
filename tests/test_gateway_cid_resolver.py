"""Tests for CID resolver."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from definitions.gateway_lib.cid.resolver import CIDResolver


class TestCIDResolver(unittest.TestCase):
    """Tests for CID content resolution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = CIDResolver()
    
    def test_create_resolver(self):
        """Test creating a CID resolver instance."""
        resolver = CIDResolver()
        self.assertIsNotNone(resolver)
    
    def test_resolve_returns_none_for_nonexistent_cid(self):
        """Test that resolve returns None for CID that doesn't exist anywhere."""
        result = self.resolver.resolve("nonexistent_cid_value_12345")
        self.assertIsNone(result)
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_from_database_with_file_data(self, mock_get_cid):
        """Test resolving CID from database with file_data attribute."""
        mock_content = Mock()
        mock_content.file_data = b"test content"
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid")
        
        self.assertEqual(result, "test content")
        mock_get_cid.assert_called_once_with("/test_cid")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_from_database_with_data_attribute(self, mock_get_cid):
        """Test resolving CID from database with data attribute."""
        mock_content = Mock()
        del mock_content.file_data  # Ensure file_data doesn't exist
        mock_content.data = b"test data"
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid")
        
        self.assertEqual(result, "test data")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_from_database_as_bytes(self, mock_get_cid):
        """Test resolving CID from database as bytes."""
        mock_content = Mock()
        mock_content.file_data = b"binary content"
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid", as_bytes=True)
        
        self.assertEqual(result, b"binary content")
        self.assertIsInstance(result, bytes)
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_adds_leading_slash(self, mock_get_cid):
        """Test that resolver adds leading slash for database lookup."""
        mock_content = Mock()
        mock_content.file_data = b"content"
        mock_get_cid.return_value = mock_content
        
        self.resolver.resolve("no_leading_slash")
        
        mock_get_cid.assert_called_once_with("/no_leading_slash")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_preserves_leading_slash(self, mock_get_cid):
        """Test that resolver preserves existing leading slash."""
        mock_content = Mock()
        mock_content.file_data = b"content"
        mock_get_cid.return_value = mock_content
        
        self.resolver.resolve("/with_leading_slash")
        
        mock_get_cid.assert_called_once_with("/with_leading_slash")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_handles_database_exception(self, mock_get_cid):
        """Test that resolver handles database exceptions gracefully."""
        mock_get_cid.side_effect = Exception("Database error")
        
        result = self.resolver.resolve("test_cid")
        
        # Should try other resolution methods, but ultimately return None
        self.assertIsNone(result)
    
    def test_resolve_from_filesystem_path(self):
        """Test resolving from filesystem path."""
        # Create a temporary file to test with
        test_file = Path("test_cid_file.txt")
        try:
            test_file.write_text("filesystem content")
            
            result = self.resolver.resolve(str(test_file))
            
            self.assertEqual(result, "filesystem content")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_resolve_from_filesystem_as_bytes(self):
        """Test resolving from filesystem as bytes."""
        test_file = Path("test_cid_binary.bin")
        try:
            test_file.write_bytes(b"binary filesystem content")
            
            result = self.resolver.resolve(str(test_file), as_bytes=True)
            
            self.assertEqual(result, b"binary filesystem content")
            self.assertIsInstance(result, bytes)
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_resolve_strips_leading_slash_for_filesystem(self):
        """Test that leading slash is stripped for filesystem lookup."""
        test_file = Path("test_file.txt")
        try:
            test_file.write_text("content")
            
            # Try to resolve with leading slash
            result = self.resolver.resolve(f"/{test_file}")
            
            self.assertEqual(result, "content")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_converts_string_to_bytes(self, mock_get_cid):
        """Test converting string data to bytes when as_bytes=True."""
        mock_content = Mock()
        mock_content.file_data = "string content"
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid", as_bytes=True)
        
        self.assertEqual(result, b"string content")
        self.assertIsInstance(result, bytes)
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_converts_bytes_to_string(self, mock_get_cid):
        """Test converting bytes data to string when as_bytes=False."""
        mock_content = Mock()
        mock_content.file_data = b"bytes content"
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid", as_bytes=False)
        
        self.assertEqual(result, "bytes content")
        self.assertIsInstance(result, str)
    
    def test_resolve_no_caching(self):
        """Test that resolver doesn't cache results."""
        # This is more of a design verification - resolver always loads fresh
        # We verify this by checking that multiple calls would go through resolution
        test_file = Path("test_no_cache.txt")
        try:
            test_file.write_text("first content")
            result1 = self.resolver.resolve(str(test_file))
            
            test_file.write_text("second content")
            result2 = self.resolver.resolve(str(test_file))
            
            # If there was caching, result2 would be "first content"
            self.assertEqual(result1, "first content")
            self.assertEqual(result2, "second content")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_direct_bytes_content(self, mock_get_cid):
        """Test resolving content that is directly bytes (no file_data or data attribute)."""
        mock_get_cid.return_value = b"direct bytes"
        
        result = self.resolver.resolve("test_cid")
        
        self.assertEqual(result, "direct bytes")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_direct_string_content(self, mock_get_cid):
        """Test resolving content that is directly a string."""
        mock_get_cid.return_value = "direct string"
        
        result = self.resolver.resolve("test_cid")
        
        self.assertEqual(result, "direct string")
    
    @patch('cid_storage.get_cid_content')
    def test_resolve_unicode_content(self, mock_get_cid):
        """Test resolving Unicode content."""
        mock_content = Mock()
        mock_content.file_data = "Hello 世界 🌍".encode("utf-8")
        mock_get_cid.return_value = mock_content
        
        result = self.resolver.resolve("test_cid")
        
        self.assertEqual(result, "Hello 世界 🌍")
    
    def test_resolve_handles_none_cid_value(self):
        """Test that resolver handles None CID value gracefully."""
        # This would happen if normalize_cid_lookup returns None
        result = self.resolver.resolve("")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
