"""Unit tests for HRX parser."""

import unittest

from hrx_parser import HRXArchive, HRXParseError


class TestHRXParser(unittest.TestCase):
    """Test the HRX parser functionality."""

    def test_parse_simple_hrx(self):
        """Test parsing a simple HRX archive with two files."""
        hrx_string = """<===> input.txt
Hello World

<===> output.txt
Goodbye World
"""
        archive = HRXArchive(hrx_string)
        self.assertEqual(len(archive.files), 2)
        self.assertIn("input.txt", archive.files)
        self.assertIn("output.txt", archive.files)
        self.assertEqual(archive.get_file("input.txt"), "Hello World\n")
        self.assertEqual(archive.get_file("output.txt"), "Goodbye World\n")

    def test_list_files(self):
        """Test listing files in an archive."""
        hrx_string = """<===> file1.txt
content1

<===> file2.txt
content2

<===> file3.txt
content3
"""
        archive = HRXArchive(hrx_string)
        files = archive.list_files()
        self.assertEqual(files, ["file1.txt", "file2.txt", "file3.txt"])

    def test_get_file(self):
        """Test retrieving file content."""
        hrx_string = """<===> test.txt
Line 1
Line 2
Line 3
"""
        archive = HRXArchive(hrx_string)
        content = archive.get_file("test.txt")
        self.assertEqual(content, "Line 1\nLine 2\nLine 3\n")

    def test_has_file(self):
        """Test checking if file exists."""
        hrx_string = """<===> exists.txt
content
"""
        archive = HRXArchive(hrx_string)
        self.assertTrue(archive.has_file("exists.txt"))
        self.assertFalse(archive.has_file("notfound.txt"))

    def test_get_nonexistent_file(self):
        """Test retrieving a non-existent file returns None."""
        hrx_string = """<===> exists.txt
content
"""
        archive = HRXArchive(hrx_string)
        self.assertIsNone(archive.get_file("notfound.txt"))

    def test_empty_archive_raises_error(self):
        """Test that an empty archive raises an error."""
        with self.assertRaises(HRXParseError):
            HRXArchive("")

    def test_whitespace_only_archive_raises_error(self):
        """Test that whitespace-only archive raises an error."""
        with self.assertRaises(HRXParseError):
            HRXArchive("   \n  \n  ")

    def test_no_boundary_raises_error(self):
        """Test that archive without boundary raises an error."""
        with self.assertRaises(HRXParseError):
            HRXArchive("some random text without boundaries")

    def test_file_with_no_content(self):
        """Test parsing a file with no content."""
        hrx_string = """<===> empty.txt

<===> another.txt
has content
"""
        archive = HRXArchive(hrx_string)
        # Empty file followed immediately by another boundary has only the single newline after the path
        self.assertEqual(archive.get_file("empty.txt"), "")
        self.assertEqual(archive.get_file("another.txt"), "has content\n")

    def test_different_boundary_lengths(self):
        """Test HRX with different boundary lengths."""
        hrx_string_short = """<=> file.txt
content
"""
        archive_short = HRXArchive(hrx_string_short)
        self.assertEqual(archive_short.get_file("file.txt"), "content\n")

        hrx_string_long = """<=====> file.txt
content
"""
        archive_long = HRXArchive(hrx_string_long)
        self.assertEqual(archive_long.get_file("file.txt"), "content\n")

    def test_file_content_with_boundary_like_text(self):
        """Test that boundary-like text in content is preserved."""
        hrx_string = """<===> test.txt
This line contains <=> which looks like a boundary
but it's part of the content
"""
        archive = HRXArchive(hrx_string)
        content = archive.get_file("test.txt")
        self.assertIn("<=>", content)

    def test_multiline_content(self):
        """Test file with multiple lines of content."""
        hrx_string = """<===> multi.txt
Line 1
Line 2
Line 3
Line 4
Line 5
"""
        archive = HRXArchive(hrx_string)
        content = archive.get_file("multi.txt")
        lines = content.split("\n")
        self.assertEqual(len(lines), 6)  # 5 lines + 1 trailing newline split
        self.assertEqual(lines[0], "Line 1")
        self.assertEqual(lines[4], "Line 5")

    def test_comment_boundary(self):
        """Test that comment boundaries are skipped."""
        hrx_string = """<===>
This is a comment

<===> file1.txt
content1

<===>
Another comment

<===> file2.txt
content2
"""
        archive = HRXArchive(hrx_string)
        self.assertEqual(len(archive.files), 2)
        self.assertIn("file1.txt", archive.files)
        self.assertIn("file2.txt", archive.files)

    def test_directory_entry(self):
        """Test parsing directory entries."""
        hrx_string = """<===> dir/

<===> dir/file.txt
content
"""
        archive = HRXArchive(hrx_string)
        self.assertIn("dir", archive.directories)
        self.assertIn("dir/file.txt", archive.files)

    def test_nested_paths(self):
        """Test files with nested paths."""
        hrx_string = """<===> dir/subdir/file.txt
nested content
"""
        archive = HRXArchive(hrx_string)
        self.assertTrue(archive.has_file("dir/subdir/file.txt"))
        self.assertEqual(archive.get_file("dir/subdir/file.txt"), "nested content\n")


if __name__ == "__main__":
    unittest.main()
