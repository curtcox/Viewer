"""Unit tests for main.py functions."""

import os
import tempfile
import unittest
from pathlib import Path


class TestGetDefaultBootCid(unittest.TestCase):
    """Tests for get_default_boot_cid function."""

    def test_boot_cid_file_exists_in_reference_templates(self):
        """Test that boot.cid exists in reference_templates directory."""
        # This test verifies that the boot.cid file was generated
        project_root = Path(__file__).parent.parent
        boot_cid_file = project_root / "reference_templates" / "boot.cid"

        # The file should exist (created by generate_boot_image.py)
        self.assertTrue(
            boot_cid_file.exists(),
            "boot.cid should exist in reference_templates directory. "
            "Run generate_boot_image.py to create it."
        )

        # The file should contain a valid CID (base64-like string)
        if boot_cid_file.exists():
            content = boot_cid_file.read_text().strip()
            self.assertGreater(len(content), 0, "boot.cid should not be empty")
            # CIDs should be reasonable length
            self.assertGreater(len(content), 20, "CID should be at least 20 characters")

    def test_boot_cid_format_valid(self):
        """Test that boot.cid contains a valid-looking CID format."""
        project_root = Path(__file__).parent.parent
        boot_cid_file = project_root / "reference_templates" / "boot.cid"

        if boot_cid_file.exists():
            content = boot_cid_file.read_text().strip()

            # CIDs are base64url encoded, so should only contain valid characters
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
            content_chars = set(content)
            self.assertTrue(
                content_chars.issubset(valid_chars),
                f"CID contains invalid characters: {content_chars - valid_chars}"
            )


if __name__ == '__main__':
    unittest.main()
