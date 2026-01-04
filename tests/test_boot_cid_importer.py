"""Tests for boot CID import functionality."""

import json
import unittest

from app import create_app, db
from boot_cid_importer import (
    extract_cid_references_from_payload,
    find_missing_cids,
    get_all_cid_paths_from_db,
    import_boot_cid,
    load_and_validate_boot_cid,
    verify_boot_cid_dependencies,
)
from cid_utils import generate_cid
from db_access import create_cid_record
from models import Alias, Export, Server


class TestBootCidImporter(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_all_cid_paths_from_db_empty(self):
        """Test getting all CID paths when database has only pre-loaded CIDs."""
        with self.app.app_context():
            paths = get_all_cid_paths_from_db()
            # The database will have CIDs loaded from the cids directory
            # Just verify it returns a set
            self.assertIsInstance(paths, set)

    def test_get_all_cid_paths_from_db_with_cids(self):
        """Test getting all CID paths includes added CIDs."""
        with self.app.app_context():
            # Create some CIDs
            content1 = b"test content 1"
            cid1 = generate_cid(content1)
            create_cid_record(cid1, content1)

            content2 = b"test content 2"
            cid2 = generate_cid(content2)
            create_cid_record(cid2, content2)

            paths = get_all_cid_paths_from_db()
            # Check that our CIDs are included (there may be others from cids directory)
            self.assertIn(f"/{cid1}", paths)
            self.assertIn(f"/{cid2}", paths)

    def test_extract_cid_references_from_payload_empty(self):
        """Test extracting CID references from empty payload."""
        payload = {}
        refs = extract_cid_references_from_payload(payload)
        self.assertEqual(refs, set())

    def test_extract_cid_references_from_payload_with_cid_values(self):
        """Test that CIDs in cid_values are NOT included in required references."""
        cid1 = generate_cid(b"content1")
        cid2 = generate_cid(b"content2")

        payload = {
            "cid_values": {
                cid1: "content1",
                cid2: "content2",
            }
        }

        refs = extract_cid_references_from_payload(payload)
        # CIDs in cid_values don't need to be in the database
        self.assertEqual(refs, set())

    def test_extract_cid_references_from_payload_with_sections(self):
        """Test extracting CID references from payload with section references."""
        aliases_cid = generate_cid(b"aliases content")
        servers_cid = generate_cid(b"servers content")

        payload = {
            "aliases": aliases_cid,
            "servers": servers_cid,
        }

        refs = extract_cid_references_from_payload(payload)
        self.assertEqual(refs, {f"/{aliases_cid}", f"/{servers_cid}"})

    def test_find_missing_cids_all_present(self):
        """Test finding missing CIDs when all are present."""
        with self.app.app_context():
            content1 = b"test content 1"
            cid1 = generate_cid(content1)
            create_cid_record(cid1, content1)

            required = {f"/{cid1}"}
            missing = find_missing_cids(required)
            self.assertEqual(missing, [])

    def test_find_missing_cids_some_missing(self):
        """Test finding missing CIDs when some are missing."""
        with self.app.app_context():
            content1 = b"test content 1"
            cid1 = generate_cid(content1)
            create_cid_record(cid1, content1)

            cid2 = generate_cid(b"missing content")

            required = {f"/{cid1}", f"/{cid2}"}
            missing = find_missing_cids(required)
            self.assertEqual(missing, [f"/{cid2}"])

    def test_load_and_validate_boot_cid_invalid_format(self):
        """Test loading boot CID with invalid format."""
        with self.app.app_context():
            payload, error = load_and_validate_boot_cid("not-a-valid-cid")
            self.assertIsNone(payload)
            self.assertIsNotNone(error)
            self.assertIn("Invalid CID format", error)

    def test_load_and_validate_boot_cid_not_found(self):
        """Test loading boot CID that doesn't exist in database (hash-based)."""
        with self.app.app_context():
            # Use content > 64 bytes to create a hash-based CID that requires DB storage
            valid_cid = generate_cid(b"x" * 100)
            payload, error = load_and_validate_boot_cid(valid_cid)
            self.assertIsNone(payload)
            self.assertIsNotNone(error)
            self.assertIn("not found in database", error)
            self.assertIn("cids directory", error)

    def test_load_and_validate_boot_cid_invalid_json(self):
        """Test loading boot CID with invalid JSON content."""
        with self.app.app_context():
            content = b"not valid json {"
            cid = generate_cid(content)
            create_cid_record(cid, content)

            payload, error = load_and_validate_boot_cid(cid)
            self.assertIsNone(payload)
            self.assertIsNotNone(error)
            self.assertIn("not valid JSON", error)

    def test_load_and_validate_boot_cid_not_utf8(self):
        """Test loading boot CID with non-UTF-8 content."""
        with self.app.app_context():
            content = b"\xff\xfe invalid utf-8"
            cid = generate_cid(content)
            create_cid_record(cid, content)

            payload, error = load_and_validate_boot_cid(cid)
            self.assertIsNone(payload)
            self.assertIsNotNone(error)
            self.assertIn("not valid UTF-8", error)

    def test_load_and_validate_boot_cid_not_object(self):
        """Test loading boot CID with JSON that's not an object."""
        with self.app.app_context():
            content = json.dumps(["not", "an", "object"]).encode("utf-8")
            cid = generate_cid(content)
            create_cid_record(cid, content)

            payload, error = load_and_validate_boot_cid(cid)
            self.assertIsNone(payload)
            self.assertIsNotNone(error)
            self.assertIn("must be a JSON object", error)

    def test_load_and_validate_boot_cid_success(self):
        """Test successfully loading and validating a boot CID."""
        with self.app.app_context():
            payload_data = {"version": 6, "aliases": []}
            content = json.dumps(payload_data).encode("utf-8")
            cid = generate_cid(content)
            create_cid_record(cid, content)

            payload, error = load_and_validate_boot_cid(cid)
            self.assertIsNone(error)
            self.assertIsNotNone(payload)
            self.assertEqual(payload, payload_data)

    def test_verify_boot_cid_dependencies_missing_cids(self):
        """Test verifying boot CID dependencies when CIDs are missing."""
        with self.app.app_context():
            # Create referenced CID that will be missing
            missing_cid = generate_cid(b"missing content")

            # Create boot CID that references the missing CID
            payload_data = {
                "version": 6,
                "aliases": missing_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            success, error = verify_boot_cid_dependencies(boot_cid)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIn("missing from the database", error)
            self.assertIn(f"/{missing_cid}", error)
            self.assertIn("cids directory", error)

    def test_verify_boot_cid_dependencies_multiple_missing_cids(self):
        """Test error message lists all missing CIDs."""
        with self.app.app_context():
            # Create multiple referenced CIDs that will be missing (referenced in sections, not cid_values)
            missing_cid1 = generate_cid(b"missing content 1")
            missing_cid2 = generate_cid(b"missing content 2")

            # Create boot CID that references the missing CIDs in sections
            payload_data = {
                "version": 6,
                "aliases": missing_cid1,
                "servers": missing_cid2,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            success, error = verify_boot_cid_dependencies(boot_cid)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            # Check both missing CIDs are listed
            self.assertIn(f"/{missing_cid1}", error)
            self.assertIn(f"/{missing_cid2}", error)

    def test_verify_boot_cid_dependencies_all_present(self):
        """Test verifying boot CID dependencies when all are present."""
        with self.app.app_context():
            # Create referenced CID
            ref_content = b"referenced content"
            ref_cid = generate_cid(ref_content)
            create_cid_record(ref_cid, ref_content)

            # Create boot CID that references the existing CID
            payload_data = {
                "version": 6,
                "aliases": ref_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            success, error = verify_boot_cid_dependencies(boot_cid)
            self.assertTrue(success)
            self.assertIsNone(error)

    def test_import_boot_cid_success(self):
        """Test successfully importing a boot CID with aliases and servers."""
        with self.app.app_context():
            # Create alias content with proper definition format
            aliases_data = [
                {
                    "name": "test-alias",
                    "definition": "/test-alias -> /test-target",
                }
            ]
            aliases_content = json.dumps(aliases_data).encode("utf-8")
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            # Create server content
            servers_data = [
                {
                    "name": "test-server",
                    "definition": 'echo "test"',
                }
            ]
            servers_content = json.dumps(servers_data).encode("utf-8")
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            # Create boot CID
            payload_data = {
                "version": 6,
                "aliases": aliases_cid,
                "servers": servers_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            if not success:
                self.fail(f"Import failed: {error}")
            self.assertTrue(success)
            self.assertIsNone(error)

            # Verify the alias was imported
            alias = Alias.query.filter_by(name="test-alias").first()
            self.assertIsNotNone(alias)

            # Verify the server was imported
            server = Server.query.filter_by(name="test-server").first()
            self.assertIsNotNone(server)

            # Verify snapshot export was generated
            snapshot_export = Export.query.order_by(Export.created_at.desc()).first()
            self.assertIsNotNone(
                snapshot_export,
                "Snapshot export should be created after boot CID import",
            )

    def test_import_boot_cid_missing_dependency(self):
        """Test importing boot CID with missing dependency fails with helpful message."""
        with self.app.app_context():
            # Create boot CID that references a non-existent CID
            missing_cid = generate_cid(b"missing content")
            payload_data = {
                "version": 6,
                "aliases": missing_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Import should fail
            success, error = import_boot_cid(self.app, boot_cid)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIn("missing from the database", error)
            self.assertIn(f"/{missing_cid}", error)

    def test_import_boot_cid_invalid_cid(self):
        """Test importing invalid boot CID fails with helpful message."""
        with self.app.app_context():
            success, error = import_boot_cid(self.app, "invalid-cid")
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIn("Invalid CID format", error)

    def test_import_boot_cid_not_found(self):
        """Test importing non-existent boot CID fails with helpful message."""
        with self.app.app_context():
            # Use content > 64 bytes to create a hash-based CID that requires DB storage
            valid_cid = generate_cid(b"x" * 100)
            success, error = import_boot_cid(self.app, valid_cid)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIn("not found in database", error)
            self.assertIn("cids directory", error)

    def test_import_boot_cid_with_cid_values_section(self):
        """Test importing boot CID that includes cid_values section."""
        with self.app.app_context():
            # Create alias content (will be in cid_values, not a separate CID)
            aliases_data = [
                {
                    "name": "test-alias-2",
                    "definition": "/test-alias-2 -> /test-target-2",
                }
            ]
            aliases_content = json.dumps(aliases_data).encode("utf-8")
            aliases_cid = generate_cid(aliases_content)

            # Create boot CID with cid_values section
            payload_data = {
                "version": 6,
                "aliases": aliases_cid,
                "cid_values": {
                    aliases_cid: aliases_content.decode("utf-8"),
                },
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Import the boot CID (aliases CID is in cid_values, not in DB)
            success, error = import_boot_cid(self.app, boot_cid)
            if not success:
                self.fail(f"Import failed: {error}")
            self.assertTrue(success)
            self.assertIsNone(error)

            # Verify the alias was imported
            alias = Alias.query.filter_by(name="test-alias-2").first()
            self.assertIsNotNone(alias)

    def test_import_boot_cid_missing_server_definition_cid_includes_diagnostics(self):
        """Missing server definition CID should include lookup diagnostics and fix guidance."""
        with self.app.app_context():
            # Generate a CID for some content, but intentionally DO NOT store it in the DB
            # and do not provide it under cid_values. This should make the import fail.
            # Use >64 bytes so we get a hash-based CID (avoids collisions with any
            # preloaded literal CIDs from the repo's cids/ directory).
            server_definition_bytes = (b'print("hello")\n' * 10) + b"missing"
            server_definition_cid = generate_cid(server_definition_bytes)

            servers_data = [
                {
                    "name": "gateway",
                    "definition_cid": server_definition_cid,
                }
            ]
            servers_content = json.dumps(servers_data).encode("utf-8")
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            payload_data = {
                "version": 6,
                "servers": servers_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Ensure the server definition CID is not present in the database.
            # (If CIDs are loaded globally from disk in this test environment, we want
            # to keep this test stable by using a CID that is not part of the repo.)
            from routes.import_export.cid_utils import normalise_cid  # pylint: disable=import-outside-toplevel
            from cid_presenter import cid_path  # pylint: disable=import-outside-toplevel
            from db_access import get_cid_by_path  # pylint: disable=import-outside-toplevel

            missing_path = cid_path(normalise_cid(server_definition_cid))
            assert missing_path is not None
            assert get_cid_by_path(missing_path) is None

            success, error = import_boot_cid(self.app, boot_cid)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIn("While importing server", error)
            self.assertIn("could not be resolved", error)
            self.assertIn("Details:", error)
            self.assertIn("Lookup order:", error)
            self.assertIn("Fix options:", error)

    def test_import_boot_cid_works_without_request_context(self):
        """Test that boot CID import works without request context (no CSRF error)."""
        with self.app.app_context():
            # Create simple alias content
            aliases_data = [
                {
                    "name": "context-test-alias",
                    "definition": "/context-test -> /target",
                }
            ]
            aliases_content = json.dumps(aliases_data).encode("utf-8")
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            # Create boot CID
            payload_data = {
                "version": 6,
                "aliases": aliases_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Import should work even without request context
            # (This would previously fail with "Working outside of request context")
            success, error = import_boot_cid(self.app, boot_cid)

            if not success:
                self.fail(f"Import failed: {error}")

            self.assertTrue(success)
            self.assertIsNone(error)

            # Verify the alias was imported
            alias = Alias.query.filter_by(name="context-test-alias").first()
            self.assertIsNotNone(alias)
            self.assertEqual(alias.definition, "/context-test -> /target")

    def test_import_boot_cid_prints_differences_to_stdout(self):
        """Test that boot CID import prints differences to stdout when DB has different data."""
        import io
        import sys

        with self.app.app_context():
            # Create existing alias in DB with different definition
            existing_alias = Alias(
                name="existing-alias",
                definition="/existing-alias -> /old-target",
                enabled=True,
            )
            db.session.add(existing_alias)
            db.session.commit()

            # Create alias content with different definition
            aliases_data = [
                {
                    "name": "existing-alias",
                    "definition": "/existing-alias -> /new-target",
                }
            ]
            aliases_content = json.dumps(aliases_data).encode("utf-8")
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            # Create boot CID
            payload_data = {
                "version": 6,
                "aliases": aliases_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Capture stdout
            captured_output = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_output

            try:
                success, error = import_boot_cid(self.app, boot_cid)
            finally:
                sys.stdout = old_stdout

            # Verify success
            self.assertTrue(success, f"Import failed: {error}")

            # Verify warning was printed to stdout
            output = captured_output.getvalue()
            self.assertIn("WARNING", output)
            self.assertIn("existing-alias", output)
            self.assertIn("different", output.lower())


if __name__ == "__main__":
    unittest.main()
