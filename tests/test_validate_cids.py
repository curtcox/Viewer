"""Tests for the CID validation script."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

# Add the scripts directory and repo root to the path
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "checks"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validate_cids import validate_cids, CidFailure
from cid_core import generate_cid


class TestValidateCids(unittest.TestCase):
    """Test CID validation logic."""

    def test_validate_cids_with_short_filename(self):
        """Test that CIDs with filenames < 94 characters are reported as failures."""
        with TemporaryDirectory() as tmpdir:
            cid_dir = Path(tmpdir)
            
            # Create a CID with a short filename (literal CID)
            short_content = b"test"
            short_cid = generate_cid(short_content)
            self.assertLess(len(short_cid), 94, "Test setup: should have short CID")
            
            short_file = cid_dir / short_cid
            short_file.write_bytes(short_content)
            
            # Run validation
            summary = validate_cids(cid_dir)
            
            # Should have 1 file, 0 valid, 1 failure
            self.assertEqual(summary.cid_count, 1)
            self.assertEqual(summary.valid_count, 0)
            self.assertEqual(len(summary.failures), 1)
            
            # Check the failure details
            failure = summary.failures[0]
            self.assertEqual(failure.filename, short_cid)
            self.assertEqual(failure.failure_type, "short_filename")
            self.assertEqual(failure.size_bytes, len(short_content))

    def test_validate_cids_with_long_filename(self):
        """Test that CIDs with filenames >= 94 characters are validated correctly."""
        with TemporaryDirectory() as tmpdir:
            cid_dir = Path(tmpdir)
            
            # Create a CID with a long filename (hashed CID)
            # Need content > 64 bytes to get a 94-char CID
            long_content = b"x" * 100
            long_cid = generate_cid(long_content)
            self.assertEqual(len(long_cid), 94, "Test setup: should have 94-char CID")
            
            long_file = cid_dir / long_cid
            long_file.write_bytes(long_content)
            
            # Run validation
            summary = validate_cids(cid_dir)
            
            # Should have 1 file, 1 valid, 0 failures
            self.assertEqual(summary.cid_count, 1)
            self.assertEqual(summary.valid_count, 1)
            self.assertEqual(len(summary.failures), 0)

    def test_validate_cids_mixed(self):
        """Test validation with both short and long filenames."""
        with TemporaryDirectory() as tmpdir:
            cid_dir = Path(tmpdir)
            
            # Create a short CID
            short_content = b"short"
            short_cid = generate_cid(short_content)
            (cid_dir / short_cid).write_bytes(short_content)
            
            # Create a long CID
            long_content = b"x" * 100
            long_cid = generate_cid(long_content)
            (cid_dir / long_cid).write_bytes(long_content)
            
            # Run validation
            summary = validate_cids(cid_dir)
            
            # Should have 2 files, 1 valid, 1 failure
            self.assertEqual(summary.cid_count, 2)
            self.assertEqual(summary.valid_count, 1)
            self.assertEqual(len(summary.failures), 1)
            self.assertEqual(len(summary.short_filename_failures), 1)
            self.assertEqual(len(summary.mismatch_failures), 0)

    def test_validate_cids_with_mismatch(self):
        """Test that mismatched CIDs are still reported correctly."""
        with TemporaryDirectory() as tmpdir:
            cid_dir = Path(tmpdir)
            
            # Create a file with wrong name
            content = b"x" * 100
            correct_cid = generate_cid(content)
            wrong_name = "A" * 94  # Wrong but right length
            
            (cid_dir / wrong_name).write_bytes(content)
            
            # Run validation
            summary = validate_cids(cid_dir)
            
            # Should have 1 file, 0 valid, 1 failure
            self.assertEqual(summary.cid_count, 1)
            self.assertEqual(summary.valid_count, 0)
            self.assertEqual(len(summary.failures), 1)
            
            # Check it's a mismatch failure, not a short filename
            failure = summary.failures[0]
            self.assertEqual(failure.failure_type, "mismatch")
            self.assertEqual(failure.computed_cid, correct_cid)
            self.assertEqual(len(summary.short_filename_failures), 0)
            self.assertEqual(len(summary.mismatch_failures), 1)

    def test_validate_cids_empty_directory(self):
        """Test validation with an empty directory."""
        with TemporaryDirectory() as tmpdir:
            cid_dir = Path(tmpdir)
            
            summary = validate_cids(cid_dir)
            
            self.assertEqual(summary.cid_count, 0)
            self.assertEqual(summary.valid_count, 0)
            self.assertEqual(len(summary.failures), 0)


if __name__ == "__main__":
    unittest.main()
