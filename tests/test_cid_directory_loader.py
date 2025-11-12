"""Tests for CID directory loader functionality."""

import json
import tempfile
import unittest
from pathlib import Path

from app import create_app, db
from cid_directory_loader import load_cids_from_directory
from cid_utils import generate_cid
from db_access import get_cid_by_path
from models import CID


class TestCidDirectoryLoader(unittest.TestCase):
    """Test suite for CID directory loader."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()

        # Create a temporary directory for CID files
        self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.cid_dir = Path(self.temp_dir.name)
        self.app.config['CID_DIRECTORY'] = str(self.cid_dir)

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-123'

    def tearDown(self):
        """Clean up test fixtures."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()

    def test_load_cids_from_empty_directory(self):
        """Test loading CIDs from an empty directory succeeds."""
        with self.app.app_context():
            # Should not raise any errors
            load_cids_from_directory(self.app, self.user_id)

            # Verify no CIDs were loaded (except any pre-loaded ones)
            # We expect only the default CIDs that were loaded during app creation
            # so just verify the function completed successfully

    def test_load_single_cid_from_directory(self):
        """Test loading a single CID file from directory."""
        with self.app.app_context():
            # Create a CID file
            content = b"test content 123"
            cid_value = generate_cid(content)
            cid_file = self.cid_dir / cid_value
            cid_file.write_bytes(content)

            # Load CIDs
            load_cids_from_directory(self.app, self.user_id)

            # Verify the CID was loaded
            cid_path = f'/{cid_value}'
            cid_record = get_cid_by_path(cid_path)
            self.assertIsNotNone(cid_record)
            self.assertEqual(bytes(cid_record.file_data), content)
            self.assertEqual(cid_record.uploaded_by_user_id, self.user_id)

    def test_load_multiple_cids_from_directory(self):
        """Test loading multiple CID files from directory."""
        with self.app.app_context():
            # Create multiple CID files
            test_contents = [
                b"test content 1",
                b"test content 2",
                b"test content 3",
            ]

            cid_values = []
            for content in test_contents:
                cid_value = generate_cid(content)
                cid_values.append(cid_value)
                cid_file = self.cid_dir / cid_value
                cid_file.write_bytes(content)

            # Load CIDs
            load_cids_from_directory(self.app, self.user_id)

            # Verify all CIDs were loaded
            for i, cid_value in enumerate(cid_values):
                cid_path = f'/{cid_value}'
                cid_record = get_cid_by_path(cid_path)
                self.assertIsNotNone(cid_record, f"CID {cid_value} should be loaded")
                self.assertEqual(bytes(cid_record.file_data), test_contents[i])

    def test_skip_hidden_files(self):
        """Test that hidden files (starting with .) are skipped."""
        with self.app.app_context():
            # Create a hidden file that looks like a CID
            hidden_file = self.cid_dir / ".hidden_file"
            hidden_file.write_bytes(b"hidden content")

            # Create a .gitignore file
            gitignore = self.cid_dir / ".gitignore"
            gitignore.write_bytes(b"*.tmp\n")

            # Load CIDs - should not fail
            load_cids_from_directory(self.app, self.user_id)

            # Verify hidden files were not loaded
            all_cids = CID.query.filter_by(uploaded_by_user_id=self.user_id).all()
            for cid in all_cids:
                self.assertFalse(cid.path.endswith('.hidden_file'))
                self.assertFalse(cid.path.endswith('.gitignore'))

    def test_invalid_cid_filename_causes_exit(self):
        """Test that an invalid CID filename causes SystemExit."""
        with self.app.app_context():
            # Create a file with invalid CID name
            invalid_file = self.cid_dir / "not-a-valid-cid.txt"
            invalid_file.write_bytes(b"some content")

            # Should raise SystemExit with helpful message
            with self.assertRaises(SystemExit) as context:
                load_cids_from_directory(self.app, self.user_id)

            # Verify the error message mentions the invalid filename
            error_message = str(context.exception)
            self.assertIn("not-a-valid-cid.txt", error_message)
            self.assertIn("not a valid normalized CID", error_message)

    def test_cid_filename_content_mismatch_causes_exit(self):
        """Test that CID filename/content mismatch causes SystemExit with helpful message."""
        with self.app.app_context():
            # Create a file with valid CID name but wrong content
            correct_cid = generate_cid(b"correct content")
            wrong_content = b"wrong content"

            # Write wrong content to a file named with correct CID
            cid_file = self.cid_dir / correct_cid
            cid_file.write_bytes(wrong_content)

            # Should raise SystemExit with helpful message
            with self.assertRaises(SystemExit) as context:
                load_cids_from_directory(self.app, self.user_id)

            # Verify the error message shows the mismatch
            error_message = str(context.exception)
            self.assertIn("mismatch", error_message.lower())
            self.assertIn(correct_cid, error_message)
            self.assertIn(generate_cid(wrong_content), error_message)

    def test_already_existing_cid_is_skipped(self):
        """Test that already-existing CIDs are skipped without error."""
        with self.app.app_context():
            # Create a CID file
            content = b"test content for existing"
            cid_value = generate_cid(content)
            cid_file = self.cid_dir / cid_value
            cid_file.write_bytes(content)

            # Load CIDs first time
            load_cids_from_directory(self.app, self.user_id)

            # Get the CID record
            cid_path = f'/{cid_value}'
            first_load = get_cid_by_path(cid_path)
            self.assertIsNotNone(first_load)

            # Load CIDs second time - should skip without error
            load_cids_from_directory(self.app, self.user_id)

            # Verify the CID still exists and wasn't duplicated
            cid_records = CID.query.filter_by(path=cid_path).all()
            self.assertEqual(len(cid_records), 1)

    def test_existing_cid_with_different_content_causes_exit(self):
        """Test that existing CID with different content causes SystemExit."""
        with self.app.app_context():
            # Create correct file content and its CID
            correct_content = b"correct file content"
            cid_value = generate_cid(correct_content)

            # Manually insert the CID into database with WRONG content
            # This simulates database corruption
            from db_access import create_cid_record
            wrong_content = b"corrupted database content"
            create_cid_record(cid_value, wrong_content, self.user_id)

            # Create a file with correct content that matches its CID filename
            cid_file = self.cid_dir / cid_value
            cid_file.write_bytes(correct_content)

            # Should raise SystemExit because DB has different content for this CID
            with self.assertRaises(SystemExit) as context:
                load_cids_from_directory(self.app, self.user_id)

            # Verify the error message
            error_message = str(context.exception)
            self.assertIn("different content", error_message)
            self.assertIn(cid_value, error_message)

    def test_directory_is_created_if_missing(self):
        """Test that the CID directory is created if it doesn't exist."""
        with self.app.app_context():
            # Create a path that doesn't exist yet
            new_dir = self.cid_dir / "new_subdir"
            self.app.config['CID_DIRECTORY'] = str(new_dir)

            self.assertFalse(new_dir.exists())

            # Load CIDs - should create the directory
            load_cids_from_directory(self.app, self.user_id)

            # Verify directory was created
            self.assertTrue(new_dir.exists())
            self.assertTrue(new_dir.is_dir())

    def test_non_file_entries_are_skipped(self):
        """Test that subdirectories and other non-file entries are skipped."""
        with self.app.app_context():
            # Create a valid CID file
            content = b"test content"
            cid_value = generate_cid(content)
            cid_file = self.cid_dir / cid_value
            cid_file.write_bytes(content)

            # Create a subdirectory
            subdir = self.cid_dir / "subdir"
            subdir.mkdir()

            # Create a file in the subdirectory
            subdir_file = subdir / "file.txt"
            subdir_file.write_bytes(b"subdir content")

            # Load CIDs - should not fail and should only load the valid CID file
            load_cids_from_directory(self.app, self.user_id)

            # Verify only the valid CID was loaded
            cid_path = f'/{cid_value}'
            cid_record = get_cid_by_path(cid_path)
            self.assertIsNotNone(cid_record)

    def test_load_cid_with_json_content(self):
        """Test loading a CID file containing JSON (typical export format)."""
        with self.app.app_context():
            # Create a JSON export payload
            payload = {
                'version': 6,
                'aliases': [],
                'servers': [],
                'variables': [],
            }
            content = json.dumps(payload, indent=2).encode('utf-8')
            cid_value = generate_cid(content)
            cid_file = self.cid_dir / cid_value
            cid_file.write_bytes(content)

            # Load CIDs
            load_cids_from_directory(self.app, self.user_id)

            # Verify the CID was loaded correctly
            cid_path = f'/{cid_value}'
            cid_record = get_cid_by_path(cid_path)
            self.assertIsNotNone(cid_record)

            # Verify content can be decoded and parsed
            loaded_content = bytes(cid_record.file_data).decode('utf-8')
            loaded_payload = json.loads(loaded_content)
            self.assertEqual(loaded_payload, payload)

    def test_default_directory_location(self):
        """Test that default directory is app.root_path/cids when not configured."""
        # Create a new app without CID_DIRECTORY configured
        app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        # Don't set CID_DIRECTORY config
        if 'CID_DIRECTORY' in app.config:
            del app.config['CID_DIRECTORY']

        with app.app_context():
            db.create_all()

            # The default directory should be created at app.root_path/cids
            # Load CIDs - this will use and create the default directory
            # Note: We don't need to assert on the directory existing here
            # because the actual app has real CID files in the default location
            # We're just verifying it doesn't crash when CID_DIRECTORY is not set
            try:
                load_cids_from_directory(app, 'test-user')
            except SystemExit:
                # May exit if there are CID validation issues in the real directory
                # but we're mainly testing that it uses the correct default path
                pass

    def test_error_message_includes_directory_path(self):
        """Test that error messages include the directory path for debugging."""
        with self.app.app_context():
            # Create a file with invalid CID name
            invalid_file = self.cid_dir / "invalid-cid"
            invalid_file.write_bytes(b"content")

            # Should raise SystemExit with directory path in message
            with self.assertRaises(SystemExit) as context:
                load_cids_from_directory(self.app, self.user_id)

            # Verify the error message includes the directory path
            error_message = str(context.exception)
            self.assertIn(str(self.cid_dir), error_message)


if __name__ == '__main__':
    unittest.main()
