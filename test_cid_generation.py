import unittest
import hashlib
import base64

from cid_utils import (
    CID_LENGTH,
    CID_NORMALIZED_PATTERN,
    generate_cid,
    is_normalized_cid,
    is_probable_cid_component,
    is_strict_cid_candidate,
    split_cid_path,
)


class TestCIDGeneration(unittest.TestCase):
    """Unit tests for CID generation functionality"""

    def test_same_content_same_cid(self):
        """Test that same content produces the same CID (content type no longer affects CID)"""
        content = b"Hello, World!"
        
        cid1 = generate_cid(content)
        cid2 = generate_cid(content)
        cid3 = generate_cid(content)
        
        # All CIDs should be identical since content type no longer affects CID generation
        self.assertEqual(cid1, cid2)
        self.assertEqual(cid1, cid3)
        self.assertEqual(cid2, cid3)

    def test_different_content_different_cids(self):
        """Test that different content produces different CIDs"""
        
        cid1 = generate_cid(b"Hello, World!")
        cid2 = generate_cid(b"Goodbye, World!")
        cid3 = generate_cid(b"")
        
        # All CIDs should be different
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_identical_content_same_cid(self):
        """Test that identical content produces the same CID"""
        content = b"Test content for CID generation"
        
        cid1 = generate_cid(content)
        cid2 = generate_cid(content)
        
        self.assertEqual(cid1, cid2)

    def test_cid_format(self):
        """Test that generated CIDs have the correct format"""
        content = b"Sample content for format testing"
        
        cid = generate_cid(content)
        
        # Should be the expected canonical length for generated CIDs
        self.assertEqual(len(cid), CID_LENGTH)

        # Should only contain characters defined for generated CIDs
        self.assertTrue(CID_NORMALIZED_PATTERN.fullmatch(cid))

    def test_empty_content(self):
        """Test CID generation with empty content"""
        
        cid1 = generate_cid(b"")
        cid2 = generate_cid(b"")
        
        # Empty content should still generate valid CIDs at the canonical length
        self.assertEqual(len(cid1), CID_LENGTH)
        self.assertEqual(len(cid2), CID_LENGTH)
        
        # Same empty content should produce same CID
        self.assertEqual(cid1, cid2)

    def test_unicode_content(self):
        """Test CID generation with unicode characters in content"""
        content = "Content with unicode: ".encode('utf-8')
        
        cid = generate_cid(content)
        
        # Should generate a valid CID
        self.assertEqual(len(cid), CID_LENGTH)

    def test_large_content(self):
        """Test CID generation with large content"""
        # Create 1MB of content
        large_content = b"A" * (1024 * 1024)
        
        cid = generate_cid(large_content)
        
        # Should still generate a valid CID
        self.assertEqual(len(cid), CID_LENGTH)

    def test_binary_content(self):
        """Test CID generation with binary content"""
        binary_content = bytes(range(256))  # All possible byte values
        
        cid = generate_cid(binary_content)
        
        # Should generate a valid CID
        self.assertEqual(len(cid), CID_LENGTH)

    def test_content_case_sensitivity(self):
        """Test that content case affects CID generation"""
        
        cid1 = generate_cid(b"text/plain")
        cid2 = generate_cid(b"TEXT/PLAIN")
        cid3 = generate_cid(b"Text/Plain")
        
        # Different cases should produce different CIDs
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_content_with_parameters(self):
        """Test CID generation with content that looks like parameters"""
        
        cid1 = generate_cid(b"text/plain")
        cid2 = generate_cid(b"text/plain; charset=utf-8")
        cid3 = generate_cid(b"text/plain; charset=iso-8859-1")
        
        # Different content should produce different CIDs
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_deterministic_generation(self):
        """Test that CID generation is deterministic across multiple calls"""
        content = b"Deterministic test content"
        
        # Generate the same CID multiple times
        cids = [generate_cid(content) for _ in range(10)]
        
        # All should be identical
        for cid in cids:
            self.assertEqual(cid, cids[0])

    def test_manual_hash_verification(self):
        """Test that the CID matches expected hash calculation"""
        content = b"Manual verification test"

        # Generate CID using our function
        actual_cid = generate_cid(content)
        
        # Calculate expected hash manually (only content, no content type)
        hasher = hashlib.sha256()
        hasher.update(content)
        sha256_hash = hasher.digest()
        
        # Encode to base64url (no padding) and create expected CID
        encoded = base64.urlsafe_b64encode(sha256_hash).decode('ascii').rstrip('=')
        expected_cid = encoded
        
        self.assertEqual(actual_cid, expected_cid)

    def test_real_world_scenarios(self):
        """Test CID generation with real-world content scenarios"""
        test_cases = [
            b"<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>",
            b'{"name": "test", "value": 123}',
            b"# Markdown Title\n\nThis is a **bold** text.",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",  # PNG header
        ]
        
        cids = []
        for i, content in enumerate(test_cases):
            with self.subTest(case=i):
                cid = generate_cid(content)
                cids.append(cid)
                
                # Verify format
                self.assertEqual(len(cid), CID_LENGTH)
        
        # All CIDs should be unique
        self.assertEqual(len(cids), len(set(cids)))

    def test_cid_helper_utilities(self):
        """Test helper functions that validate and parse CID values."""
        cid = generate_cid(b"helper utilities")

        # Validation helpers should recognise generated CIDs
        self.assertTrue(is_normalized_cid(cid))
        self.assertTrue(is_probable_cid_component(cid))
        self.assertTrue(is_strict_cid_candidate(cid))

        # Short or malformed values should fail validation
        self.assertFalse(is_probable_cid_component("short"))
        self.assertFalse(is_normalized_cid(f"{cid}extra"))

        # Path splitting should handle raw CIDs, extensions, and query parameters
        self.assertEqual(split_cid_path(f"/{cid}"), (cid, None))
        self.assertEqual(split_cid_path(f"/{cid}.json"), (cid, "json"))
        self.assertEqual(split_cid_path(f"/{cid}.html?download=1"), (cid, "html"))
        self.assertEqual(split_cid_path(f"/{cid}.txt#section"), (cid, "txt"))

        # Invalid paths should return None
        self.assertIsNone(split_cid_path("/not/a/cid"))
        self.assertIsNone(split_cid_path(""))


if __name__ == '__main__':
    unittest.main()
