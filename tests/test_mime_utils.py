"""Unit tests for mime_utils module."""

import unittest

from mime_utils import (
    EXTENSION_TO_MIME,
    MIME_TO_EXTENSION,
    extract_filename_from_cid_path,
    get_extension_from_mime_type,
    get_mime_type_from_extension,
)


class TestMIMETypeMappings(unittest.TestCase):
    """Tests for MIME type mapping dictionaries."""

    def test_extension_to_mime_has_common_types(self):
        """Test that common file extensions are mapped."""
        self.assertEqual(EXTENSION_TO_MIME["txt"], "text/plain")
        self.assertEqual(EXTENSION_TO_MIME["html"], "text/html")
        self.assertEqual(EXTENSION_TO_MIME["json"], "application/json")
        self.assertEqual(EXTENSION_TO_MIME["pdf"], "application/pdf")
        self.assertEqual(EXTENSION_TO_MIME["png"], "image/png")
        self.assertEqual(EXTENSION_TO_MIME["jpg"], "image/jpeg")

    def test_mime_to_extension_reverse_lookup(self):
        """Test reverse MIME type lookup."""
        self.assertEqual(MIME_TO_EXTENSION["text/plain"], "txt")
        self.assertEqual(MIME_TO_EXTENSION["text/html"], "html")
        self.assertEqual(MIME_TO_EXTENSION["application/json"], "json")


class TestGetMimeTypeFromExtension(unittest.TestCase):
    """Tests for get_mime_type_from_extension function."""

    def test_common_extensions(self):
        """Test MIME type detection for common extensions."""
        self.assertEqual(get_mime_type_from_extension("file.txt"), "text/plain")
        self.assertEqual(get_mime_type_from_extension("page.html"), "text/html")
        self.assertEqual(get_mime_type_from_extension("data.json"), "application/json")
        self.assertEqual(get_mime_type_from_extension("image.png"), "image/png")

    def test_path_with_directories(self):
        """Test MIME type detection from full paths."""
        self.assertEqual(
            get_mime_type_from_extension("/path/to/file.txt"), "text/plain"
        )

    def test_case_insensitive(self):
        """Test that extension matching is case-insensitive."""
        self.assertEqual(get_mime_type_from_extension("FILE.TXT"), "text/plain")
        self.assertEqual(get_mime_type_from_extension("File.Html"), "text/html")

    def test_unknown_extension(self):
        """Test unknown extensions return default MIME type."""
        self.assertEqual(
            get_mime_type_from_extension("file.unknown"), "application/octet-stream"
        )

    def test_no_extension(self):
        """Test files without extensions return default MIME type."""
        self.assertEqual(
            get_mime_type_from_extension("filename"), "application/octet-stream"
        )


class TestGetExtensionFromMimeType(unittest.TestCase):
    """Tests for get_extension_from_mime_type function."""

    def test_common_mime_types(self):
        """Test extension detection for common MIME types."""
        self.assertEqual(get_extension_from_mime_type("text/plain"), "txt")
        self.assertEqual(get_extension_from_mime_type("text/html"), "html")
        self.assertEqual(get_extension_from_mime_type("application/json"), "json")
        self.assertEqual(get_extension_from_mime_type("image/png"), "png")

    def test_mime_with_parameters(self):
        """Test MIME types with parameters (e.g., charset)."""
        self.assertEqual(
            get_extension_from_mime_type("text/plain; charset=utf-8"), "txt"
        )
        self.assertEqual(
            get_extension_from_mime_type("application/json; charset=utf-8"), "json"
        )

    def test_unknown_mime_type(self):
        """Test unknown MIME types return empty string."""
        self.assertEqual(get_extension_from_mime_type("application/unknown"), "")

    def test_case_insensitive(self):
        """Test MIME type matching is case-insensitive."""
        self.assertEqual(get_extension_from_mime_type("TEXT/PLAIN"), "txt")
        self.assertEqual(get_extension_from_mime_type("Image/PNG"), "png")


class TestExtractFilenameFromCIDPath(unittest.TestCase):
    """Tests for extract_filename_from_cid_path function."""

    def test_cid_with_filename_and_extension(self):
        """Test extracting filename from CID path."""
        result = extract_filename_from_cid_path("/CID123.document.pdf")
        self.assertEqual(result, "document.pdf")

        result = extract_filename_from_cid_path("/CID123.report.txt")
        self.assertEqual(result, "report.txt")

    def test_cid_with_only_extension(self):
        """Test CID with only extension (no filename)."""
        result = extract_filename_from_cid_path("/CID123.txt")
        self.assertIsNone(result)

        result = extract_filename_from_cid_path("/CID123.pdf")
        self.assertIsNone(result)

    def test_cid_with_multiple_dots_in_filename(self):
        """Test filenames with multiple dots."""
        result = extract_filename_from_cid_path("/CID123.my.file.txt")
        self.assertEqual(result, "my.file.txt")

        result = extract_filename_from_cid_path("/CID123.version.1.2.3.json")
        self.assertEqual(result, "version.1.2.3.json")

    def test_cid_without_extension(self):
        """Test CID without extension."""
        result = extract_filename_from_cid_path("/CID123")
        self.assertIsNone(result)

    def test_path_without_leading_slash(self):
        """Test paths without leading slash."""
        result = extract_filename_from_cid_path("CID123.document.pdf")
        self.assertEqual(result, "document.pdf")

    def test_empty_and_invalid_paths(self):
        """Test empty and invalid paths."""
        self.assertIsNone(extract_filename_from_cid_path(""))
        self.assertIsNone(extract_filename_from_cid_path("."))
        self.assertIsNone(extract_filename_from_cid_path(".."))


if __name__ == "__main__":
    unittest.main()
