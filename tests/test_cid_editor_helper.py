"""Unit tests for cid_editor_helper module."""

import unittest

from cid_core import generate_cid, DIRECT_CONTENT_EMBED_LIMIT
from cid_editor_helper import (
    CidContentStatus,
    check_cid_content,
    generate_cid_from_content,
)


class TestCheckCidContent(unittest.TestCase):
    """Tests for check_cid_content function."""

    def test_empty_value_is_not_cid(self):
        """Test that empty string is not a CID."""
        result = check_cid_content("")
        self.assertFalse(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.NOT_A_CID)

    def test_none_value_is_not_cid(self):
        """Test that None-like empty string is not a CID."""
        result = check_cid_content("   ")
        self.assertFalse(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.NOT_A_CID)

    def test_regular_text_is_not_cid(self):
        """Test that regular text is not a CID."""
        result = check_cid_content("Hello, World!")
        self.assertFalse(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.NOT_A_CID)

    def test_short_string_is_not_cid(self):
        """Test that short strings are not CIDs."""
        result = check_cid_content("ABC123")
        self.assertFalse(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.NOT_A_CID)

    def test_invalid_cid_format(self):
        """Test that invalid CID format is not a CID."""
        result = check_cid_content("AAAAAAA!")  # Invalid characters
        self.assertFalse(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.NOT_A_CID)

    def test_empty_content_cid(self):
        """Test CID for empty content."""
        cid = generate_cid(b"")
        result = check_cid_content(cid)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.cid_value, cid)
        self.assertEqual(result.content, b"")
        self.assertEqual(result.content_text, "")

    def test_small_content_cid(self):
        """Test CID with directly embedded content."""
        content = b"Hello, World!"
        cid = generate_cid(content)
        result = check_cid_content(cid)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.cid_value, cid)
        self.assertEqual(result.content, content)
        self.assertEqual(result.content_text, "Hello, World!")

    def test_boundary_content_cid(self):
        """Test CID at the boundary of direct embedding."""
        content = b"x" * DIRECT_CONTENT_EMBED_LIMIT
        cid = generate_cid(content)
        result = check_cid_content(cid)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.content, content)

    def test_large_content_cid_not_found(self):
        """Test CID for large content that's not in database."""
        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1)
        cid = generate_cid(content)
        result = check_cid_content(cid)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_NOT_FOUND)
        self.assertEqual(result.cid_value, cid)
        self.assertIsNone(result.content)

    def test_cid_with_whitespace(self):
        """Test CID with surrounding whitespace is still recognized."""
        content = b"test"
        cid = generate_cid(content)
        result = check_cid_content(f"  {cid}  ")
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.content, content)

    def test_binary_content_no_text(self):
        """Test that binary content that's not valid UTF-8 returns None for content_text."""
        # Create content with invalid UTF-8 bytes
        content = bytes([0xFF, 0xFE, 0x00, 0x01])
        cid = generate_cid(content)
        result = check_cid_content(cid)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.content, content)
        self.assertIsNone(result.content_text)


class TestGenerateCidFromContent(unittest.TestCase):
    """Tests for generate_cid_from_content function."""

    def test_generate_cid_from_empty_string(self):
        """Test generating CID from empty string."""
        cid_value, content_bytes = generate_cid_from_content("")
        self.assertEqual(cid_value, "AAAAAAAA")
        self.assertEqual(content_bytes, b"")

    def test_generate_cid_from_text(self):
        """Test generating CID from text content."""
        cid_value, content_bytes = generate_cid_from_content("Hello")
        self.assertEqual(content_bytes, b"Hello")
        # Verify the CID is valid
        self.assertTrue(len(cid_value) >= 8)

    def test_roundtrip(self):
        """Test that generated CID can be checked back."""
        original_text = "Test content for roundtrip"
        cid_value, _ = generate_cid_from_content(original_text)

        result = check_cid_content(cid_value)
        self.assertTrue(result.is_cid)
        self.assertEqual(result.status, CidContentStatus.CONTENT_EMBEDDED)
        self.assertEqual(result.content_text, original_text)


if __name__ == "__main__":
    unittest.main()
