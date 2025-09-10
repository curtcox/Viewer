import unittest
import hashlib
import base64
from routes import generate_cid


class TestCIDGeneration(unittest.TestCase):
    """Unit tests for CID generation functionality"""

    def test_same_content_different_types_different_cids(self):
        """Test that same content with different content types produces different CIDs"""
        content = b"Hello, World!"
        
        cid_text = generate_cid(content, "text/plain")
        cid_html = generate_cid(content, "text/html")
        cid_json = generate_cid(content, "application/json")
        
        # All CIDs should be different
        self.assertNotEqual(cid_text, cid_html)
        self.assertNotEqual(cid_text, cid_json)
        self.assertNotEqual(cid_html, cid_json)

    def test_different_content_same_type_different_cids(self):
        """Test that different content with same content type produces different CIDs"""
        content_type = "text/plain"
        
        cid1 = generate_cid(b"Hello, World!", content_type)
        cid2 = generate_cid(b"Goodbye, World!", content_type)
        cid3 = generate_cid(b"", content_type)
        
        # All CIDs should be different
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_identical_content_and_type_same_cid(self):
        """Test that identical content and content type produces the same CID"""
        content = b"Test content for CID generation"
        content_type = "text/markdown"
        
        cid1 = generate_cid(content, content_type)
        cid2 = generate_cid(content, content_type)
        
        self.assertEqual(cid1, cid2)

    def test_cid_format(self):
        """Test that generated CIDs have the correct format"""
        content = b"Test content"
        content_type = "text/plain"
        
        cid = generate_cid(content, content_type)
        
        # Should start with 'bafybei'
        self.assertTrue(cid.startswith('bafybei'))
        
        # Should be exactly 59 characters (bafybei + 52 chars)
        self.assertEqual(len(cid), 59)
        
        # Should only contain lowercase letters and numbers (base32)
        import re
        self.assertTrue(re.match(r'^bafybei[a-z2-7]+$', cid))

    def test_empty_content(self):
        """Test CID generation with empty content"""
        cid1 = generate_cid(b"", "text/plain")
        cid2 = generate_cid(b"", "application/json")
        
        # Should generate valid CIDs
        self.assertTrue(cid1.startswith('bafybei'))
        self.assertTrue(cid2.startswith('bafybei'))
        
        # Different content types should produce different CIDs even with empty content
        self.assertNotEqual(cid1, cid2)

    def test_unicode_content_type(self):
        """Test CID generation with unicode characters in content type"""
        content = b"Test content"
        content_type = "text/plain; charset=utf-8"
        
        cid = generate_cid(content, content_type)
        
        # Should generate a valid CID
        self.assertTrue(cid.startswith('bafybei'))
        self.assertEqual(len(cid), 59)

    def test_large_content(self):
        """Test CID generation with large content"""
        # Create 1MB of content
        large_content = b"A" * (1024 * 1024)
        content_type = "application/octet-stream"
        
        cid = generate_cid(large_content, content_type)
        
        # Should still generate a valid CID
        self.assertTrue(cid.startswith('bafybei'))
        self.assertEqual(len(cid), 59)

    def test_binary_content(self):
        """Test CID generation with binary content"""
        # Create some binary content
        binary_content = bytes(range(256))
        content_type = "application/octet-stream"
        
        cid = generate_cid(binary_content, content_type)
        
        # Should generate a valid CID
        self.assertTrue(cid.startswith('bafybei'))
        self.assertEqual(len(cid), 59)

    def test_content_type_case_sensitivity(self):
        """Test that content type case affects CID generation"""
        content = b"Test content"
        
        cid1 = generate_cid(content, "text/plain")
        cid2 = generate_cid(content, "TEXT/PLAIN")
        cid3 = generate_cid(content, "Text/Plain")
        
        # All should be different due to case sensitivity
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_content_type_parameters(self):
        """Test that content type parameters affect CID generation"""
        content = b"Test content"
        
        cid1 = generate_cid(content, "text/plain")
        cid2 = generate_cid(content, "text/plain; charset=utf-8")
        cid3 = generate_cid(content, "text/plain; charset=iso-8859-1")
        
        # All should be different due to different parameters
        self.assertNotEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid3)
        self.assertNotEqual(cid2, cid3)

    def test_deterministic_generation(self):
        """Test that CID generation is deterministic across multiple calls"""
        content = b"Deterministic test content"
        content_type = "text/plain; charset=utf-8"
        
        # Generate CID multiple times
        cids = [generate_cid(content, content_type) for _ in range(10)]
        
        # All should be identical
        for cid in cids:
            self.assertEqual(cid, cids[0])

    def test_manual_hash_verification(self):
        """Test that the CID matches expected hash calculation"""
        content = b"Test"
        content_type = "text/plain"
        
        # Calculate expected hash manually
        hasher = hashlib.sha256()
        hasher.update(content)
        hasher.update(content_type.encode('utf-8'))
        expected_hash = hasher.digest()
        expected_encoded = base64.b32encode(expected_hash).decode('ascii').lower().rstrip('=')
        expected_cid = f"bafybei{expected_encoded[:52]}"
        
        # Compare with function output
        actual_cid = generate_cid(content, content_type)
        self.assertEqual(actual_cid, expected_cid)

    def test_real_world_scenarios(self):
        """Test CID generation with real-world content scenarios"""
        scenarios = [
            (b'{"name": "test", "value": 123}', "application/json"),
            (b'<html><body>Hello</body></html>', "text/html"),
            (b'# Markdown Title\n\nSome content', "text/markdown"),
            (b'SELECT * FROM users;', "text/x-sql"),
            (b'def hello():\n    print("Hello")', "text/x-python"),
            (b'body { color: red; }', "text/css"),
            (b'console.log("Hello");', "application/javascript"),
        ]
        
        cids = []
        for content, content_type in scenarios:
            cid = generate_cid(content, content_type)
            cids.append(cid)
            
            # Verify format
            self.assertTrue(cid.startswith('bafybei'))
            self.assertEqual(len(cid), 59)
        
        # All CIDs should be unique
        self.assertEqual(len(cids), len(set(cids)))


if __name__ == '__main__':
    unittest.main()
