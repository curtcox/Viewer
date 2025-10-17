#!/usr/bin/env python3
"""
Integration test for the serve_cid_content function with content disposition logic.
This test directly imports and tests the extract_filename_from_cid_path function.
"""

import unittest
import sys
import os

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cid_utils import extract_filename_from_cid_path


class TestExtractFilenameFromCidPath(unittest.TestCase):
    """Test the extract_filename_from_cid_path function directly"""

    def test_cid_only_returns_none(self):
        """Test /{CID} - should return None"""
        test_cases = [
            "/bafybeihelloworld123456789012345678901234567890123456",
            "/abc123",
            "/short",
            "/bafybeiverylongcidthatrepresentscontentaddressablestorage"
        ]
        
        for path in test_cases:
            with self.subTest(path=path):
                result = extract_filename_from_cid_path(path)
                self.assertIsNone(result, f"Path {path} should not return filename")

    def test_cid_with_extension_returns_none(self):
        """Test /{CID}.{ext} - should return None"""
        test_cases = [
            "/bafybeihelloworld123456789012345678901234567890123456.txt",
            "/bafybeihelloworld123456789012345678901234567890123456.html",
            "/bafybeihelloworld123456789012345678901234567890123456.json",
            "/bafybeihelloworld123456789012345678901234567890123456.pdf",
            "/abc123.csv",
            "/short.py"
        ]
        
        for path in test_cases:
            with self.subTest(path=path):
                result = extract_filename_from_cid_path(path)
                self.assertIsNone(result, f"Path {path} should not return filename")

    def test_cid_with_filename_returns_filename(self):
        """Test /{CID}.{filename}.{ext} - should return filename.ext"""
        test_cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.document.txt", "document.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.report.pdf", "report.pdf"),
            ("/bafybeihelloworld123456789012345678901234567890123456.data.json", "data.json"),
            ("/bafybeihelloworld123456789012345678901234567890123456.page.html", "page.html"),
            ("/abc123.myfile.csv", "myfile.csv"),
            ("/cid.test.py", "test.py")
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_cid_path(path)
                self.assertEqual(result, expected_filename)

    def test_filename_with_multiple_dots(self):
        """Test filenames with multiple dots are handled correctly"""
        test_cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.my.data.file.txt", "my.data.file.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.version.1.2.3.json", "version.1.2.3.json"),
            ("/abc123.backup.2024.01.15.sql", "backup.2024.01.15.sql"),
            ("/cid.file.name.with.many.dots.ext", "file.name.with.many.dots.ext")
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_cid_path(path)
                self.assertEqual(result, expected_filename)

    def test_edge_cases(self):
        """Test edge cases"""
        test_cases = [
            ("", None),  # Empty string
            ("/", None),  # Just slash
            ("/.", None),  # Just dot
            ("/..", None),  # Two dots
            ("/a.b.c", "b.c"),  # Minimal valid case
            ("no-leading-slash.file.txt", "file.txt"),  # No leading slash
        ]
        
        for path, expected in test_cases:
            with self.subTest(path=path, expected=expected):
                result = extract_filename_from_cid_path(path)
                self.assertEqual(result, expected)

    def test_special_characters_in_filename(self):
        """Test that filenames with special characters are preserved"""
        test_cases = [
            ("/cid.file with spaces.txt", "file with spaces.txt"),
            ("/cid.file-with-dashes.txt", "file-with-dashes.txt"),
            ("/cid.file_with_underscores.txt", "file_with_underscores.txt"),
            ("/cid.file(with)parentheses.txt", "file(with)parentheses.txt"),
            ("/cid.file[with]brackets.txt", "file[with]brackets.txt"),
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_cid_path(path)
                self.assertEqual(result, expected_filename)


class TestContentDispositionBehavior(unittest.TestCase):
    """Test the expected behavior of content disposition headers"""

    def test_content_disposition_rules(self):
        """Test the rules for when content disposition should be set"""
        # Rule 1: /{CID} - no content disposition
        cid_only_paths = [
            "/bafybeihelloworld123456789012345678901234567890123456",
            "/abc123def456",
        ]
        
        for path in cid_only_paths:
            filename = extract_filename_from_cid_path(path)
            self.assertIsNone(filename, f"CID-only path {path} should not have content disposition")

        # Rule 2: /{CID}.{ext} - no content disposition  
        cid_ext_paths = [
            "/bafybeihelloworld123456789012345678901234567890123456.txt",
            "/abc123def456.json",
        ]
        
        for path in cid_ext_paths:
            filename = extract_filename_from_cid_path(path)
            self.assertIsNone(filename, f"CID.ext path {path} should not have content disposition")

        # Rule 3: /{CID}.{filename}.{ext} - set content disposition
        cid_filename_paths = [
            ("/bafybeihelloworld123456789012345678901234567890123456.document.txt", "document.txt"),
            ("/abc123def456.report.pdf", "report.pdf"),
        ]
        
        for path, expected_filename in cid_filename_paths:
            filename = extract_filename_from_cid_path(path)
            self.assertEqual(filename, expected_filename, f"CID.filename.ext path {path} should return filename {expected_filename}")

    def test_realistic_scenarios(self):
        """Test realistic usage scenarios"""
        scenarios = [
            # User uploads a file called "resume.pdf"
            ("/bafybeiabcdef123456789.resume.pdf", "resume.pdf"),
            
            # User uploads "data-export-2024.csv"  
            ("/bafybei987654321.data-export-2024.csv", "data-export-2024.csv"),
            
            # User uploads "my presentation.pptx"
            ("/bafybeixyz789.my presentation.pptx", "my presentation.pptx"),
            
            # Server generates HTML content (no filename)
            ("/bafybeiserver123.html", None),
            
            # Server generates JSON API response (no filename)
            ("/bafybeiapi456.json", None),
            
            # Direct CID access (no filename)
            ("/bafybeidirect789", None),
        ]
        
        for path, expected_filename in scenarios:
            with self.subTest(path=path, expected=expected_filename):
                result = extract_filename_from_cid_path(path)
                self.assertEqual(result, expected_filename)


if __name__ == '__main__':
    unittest.main()
