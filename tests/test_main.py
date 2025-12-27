"""Unit tests for main.py functions."""

import unittest
from pathlib import Path


class TestGetDefaultBootCid(unittest.TestCase):
    """Tests for get_default_boot_cid function."""

    def setUp(self):
        """Set up test fixtures - verify boot.cid exists before running tests."""
        project_root = Path(__file__).parent.parent
        self.boot_cid_file = project_root / "reference_templates" / "boot.cid"

        # Fail fast if boot.cid doesn't exist - don't silently pass
        self.assertTrue(
            self.boot_cid_file.exists(),
            "boot.cid must exist in reference_templates directory. "
            "Run generate_boot_image.py to create it.",
        )

    def test_boot_cid_file_exists_and_valid_content(self):
        """Test that boot.cid exists and has valid content."""
        # Read the file content once
        file_content = self.boot_cid_file.read_text().strip()

        # Verify content is not empty
        self.assertGreater(len(file_content), 0, "boot.cid should not be empty")

        # CIDs should be reasonable length
        self.assertGreater(
            len(file_content), 20, "CID should be at least 20 characters"
        )

        # Test that get_default_boot_cid() returns the same value
        # Only test if dependencies are available (full test environment)
        try:
            from main import get_default_boot_cid

            result = get_default_boot_cid()

            # Should return the file content
            self.assertIsNotNone(result, "get_default_boot_cid should return a value")
            self.assertEqual(
                result,
                file_content,
                "get_default_boot_cid should return the same CID as in boot.cid",
            )

            # Verify length expectations are met
            self.assertGreater(len(result), 0, "Returned CID should not be empty")
            self.assertGreater(
                len(result), 20, "Returned CID should be at least 20 characters"
            )
        except ModuleNotFoundError as e:
            # Skip function test if dependencies not available (e.g., logfire)
            # The integration tests will verify the actual behavior
            self.skipTest(f"Skipping function test - missing dependency: {e}")

    def test_boot_cid_format_valid(self):
        """Test that boot.cid contains a valid-looking CID format."""
        content = self.boot_cid_file.read_text().strip()

        # CIDs are base64url encoded, so should only contain valid characters
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        content_chars = set(content)
        self.assertTrue(
            content_chars.issubset(valid_chars),
            f"CID contains invalid characters: {content_chars - valid_chars}",
        )


class TestShouldUseDefaultBootCid(unittest.TestCase):
    def test_returns_true_when_no_url_and_no_cid(self):
        from main import should_use_default_boot_cid

        assert should_use_default_boot_cid(cid=None, url=None) is True

    def test_returns_false_for_internal_path_url(self):
        from main import should_use_default_boot_cid

        assert should_use_default_boot_cid(cid=None, url="/variables.txt") is False

    def test_returns_false_for_external_url(self):
        from main import should_use_default_boot_cid

        assert (
            should_use_default_boot_cid(cid=None, url="https://example.com") is False
        )

    def test_returns_false_when_cid_is_provided(self):
        from main import should_use_default_boot_cid

        assert (
            should_use_default_boot_cid(cid="AAAAA-somecid", url="/variables.txt")
            is False
        )


if __name__ == "__main__":
    unittest.main()
