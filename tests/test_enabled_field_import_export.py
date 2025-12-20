"""
Integration tests for enabled field in import/export operations.

This module tests that the enabled field is properly preserved during export
and import operations across all entity types (Alias, Server, Variable, Secret).

Issue: The enabled field was not persisting False values, causing export
operations to show enabled=True for all entities regardless of actual state.
"""

import json
import unittest

from app import create_app
from database import db
from models import Alias, Server, Variable, Secret
from alias_definition import format_primary_alias_line


class TestEnabledFieldImportExport(unittest.TestCase):
    """Integration tests for enabled field in import/export operations."""

    def setUp(self):
        """Set up test fixtures with in-memory SQLite database."""
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WTF_CSRF_ENABLED": False,
                "SECRET_KEY": "test-secret-key",
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_test_entities(self, enabled_state):
        """Helper to create test entities with specified enabled state."""
        alias_definition = format_primary_alias_line(
            "literal",
            f"/alias-{enabled_state}",
            "/target",
            alias_name=f"alias-{enabled_state}",
        )

        with self.app.app_context():
            entities = [
                Alias(
                    name=f"alias-{enabled_state}",
                    definition=alias_definition,
                    enabled=enabled_state,
                ),
                Server(
                    name=f"server-{enabled_state}",
                    definition='def main():\n    return "test"\n',
                    enabled=enabled_state,
                ),
                Variable(
                    name=f"variable-{enabled_state}",
                    definition="test-value",
                    enabled=enabled_state,
                ),
                Secret(
                    name=f"secret-{enabled_state}",
                    definition="test-secret",
                    enabled=enabled_state,
                ),
            ]
            db.session.add_all(entities)
            db.session.commit()

    def _export_entities(self):
        """Helper to export all entities."""
        response = self.client.post(
            "/export",
            data={
                "include_aliases": "y",
                "include_disabled_aliases": "y",
                "include_servers": "y",
                "include_disabled_servers": "y",
                "include_variables": "y",
                "include_disabled_variables": "y",
                "include_secrets": "y",
                "include_disabled_secrets": "y",
                "include_history": "",
                "include_cid_map": "y",
                "secret_key": "test-passphrase",
                "submit": True,
            },
        )
        return response

    def _load_export_payload_from_response(self, response):
        """Extract and parse export payload from response."""
        # The response contains HTML with the download link
        # We need to parse out the JSON from the Export table
        self.assertEqual(response.status_code, 200)

        # The export is saved to the Export table, get the latest one
        with self.app.app_context():
            from models import Export, CID

            export = Export.query.order_by(Export.created_at.desc()).first()
            self.assertIsNotNone(export, "Export should be saved")

            cid_record = CID.query.filter_by(path=f"/{export.cid}").first()
            self.assertIsNotNone(cid_record, "Export CID should exist")

            payload = json.loads(cid_record.file_data.decode("utf-8"))
            return payload

    def _load_section_from_payload(self, payload, section_key):
        """Load a section from the export payload."""
        section_cid = payload.get(section_key)
        if section_cid is None:
            return None

        cid_values = payload.get("cid_values", {})
        entry = cid_values.get(section_cid)

        if entry is None:
            # Try to load from database
            with self.app.app_context():
                from models import CID

                record = CID.query.filter_by(path=f"/{section_cid}").first()
                if record:
                    entry = record.file_data.decode("utf-8")

        if isinstance(entry, str):
            content = entry
        else:
            raise ValueError(f"Unexpected entry type: {type(entry)}")

        return json.loads(content)

    def test_export_disabled_entities_preserves_enabled_false(self):
        """Test that exporting disabled entities preserves enabled=False."""
        self._create_test_entities(enabled_state=False)
        response = self._export_entities()
        payload = self._load_export_payload_from_response(response)

        # Load sections
        alias_entries = self._load_section_from_payload(payload, "aliases")
        server_entries = self._load_section_from_payload(payload, "servers")
        variable_entries = self._load_section_from_payload(payload, "variables")
        secrets_section = self._load_section_from_payload(payload, "secrets")

        # Find disabled entities
        disabled_alias = next(
            (a for a in alias_entries if a["name"] == "alias-False"), None
        )
        disabled_server = next(
            (s for s in server_entries if s["name"] == "server-False"), None
        )
        disabled_variable = next(
            (v for v in variable_entries if v["name"] == "variable-False"), None
        )
        disabled_secret = next(
            (s for s in secrets_section["items"] if s["name"] == "secret-False"), None
        )

        # Verify all entities were exported
        self.assertIsNotNone(disabled_alias, "Disabled alias should be exported")
        self.assertIsNotNone(disabled_server, "Disabled server should be exported")
        self.assertIsNotNone(disabled_variable, "Disabled variable should be exported")
        self.assertIsNotNone(disabled_secret, "Disabled secret should be exported")

        # Verify enabled=False is preserved
        self.assertFalse(disabled_alias["enabled"], "Alias should have enabled=False")
        self.assertFalse(disabled_server["enabled"], "Server should have enabled=False")
        self.assertFalse(
            disabled_variable["enabled"], "Variable should have enabled=False"
        )
        self.assertFalse(disabled_secret["enabled"], "Secret should have enabled=False")

    def test_export_enabled_entities_preserves_enabled_true(self):
        """Test that exporting enabled entities preserves enabled=True."""
        self._create_test_entities(enabled_state=True)
        response = self._export_entities()
        payload = self._load_export_payload_from_response(response)

        # Load sections
        alias_entries = self._load_section_from_payload(payload, "aliases")
        server_entries = self._load_section_from_payload(payload, "servers")
        variable_entries = self._load_section_from_payload(payload, "variables")
        secrets_section = self._load_section_from_payload(payload, "secrets")

        # Find enabled entities
        enabled_alias = next(
            (a for a in alias_entries if a["name"] == "alias-True"), None
        )
        enabled_server = next(
            (s for s in server_entries if s["name"] == "server-True"), None
        )
        enabled_variable = next(
            (v for v in variable_entries if v["name"] == "variable-True"), None
        )
        enabled_secret = next(
            (s for s in secrets_section["items"] if s["name"] == "secret-True"), None
        )

        # Verify all entities were exported
        self.assertIsNotNone(enabled_alias, "Enabled alias should be exported")
        self.assertIsNotNone(enabled_server, "Enabled server should be exported")
        self.assertIsNotNone(enabled_variable, "Enabled variable should be exported")
        self.assertIsNotNone(enabled_secret, "Enabled secret should be exported")

        # Verify enabled=True is preserved
        self.assertTrue(enabled_alias["enabled"], "Alias should have enabled=True")
        self.assertTrue(enabled_server["enabled"], "Server should have enabled=True")
        self.assertTrue(
            enabled_variable["enabled"], "Variable should have enabled=True"
        )
        self.assertTrue(enabled_secret["enabled"], "Secret should have enabled=True")

    def test_export_mixed_enabled_states(self):
        """Test exporting entities with mixed enabled states."""
        # Create both enabled and disabled entities
        self._create_test_entities(enabled_state=True)
        self._create_test_entities(enabled_state=False)

        response = self._export_entities()
        payload = self._load_export_payload_from_response(response)

        # Load sections
        alias_entries = self._load_section_from_payload(payload, "aliases")
        server_entries = self._load_section_from_payload(payload, "servers")

        # Find both enabled and disabled entities
        enabled_alias = next(
            (a for a in alias_entries if a["name"] == "alias-True"), None
        )
        disabled_alias = next(
            (a for a in alias_entries if a["name"] == "alias-False"), None
        )

        enabled_server = next(
            (s for s in server_entries if s["name"] == "server-True"), None
        )
        disabled_server = next(
            (s for s in server_entries if s["name"] == "server-False"), None
        )

        # Verify both states are present and correct
        self.assertIsNotNone(enabled_alias)
        self.assertIsNotNone(disabled_alias)
        self.assertTrue(enabled_alias["enabled"], "Enabled alias should be True")
        self.assertFalse(disabled_alias["enabled"], "Disabled alias should be False")

        self.assertIsNotNone(enabled_server)
        self.assertIsNotNone(disabled_server)
        self.assertTrue(enabled_server["enabled"], "Enabled server should be True")
        self.assertFalse(disabled_server["enabled"], "Disabled server should be False")

    def test_disabled_entities_retrieved_correctly_before_export(self):
        """Test that disabled entities are correctly retrieved from DB before export."""
        self._create_test_entities(enabled_state=False)

        # Verify entities are disabled in database before export
        with self.app.app_context():
            alias = Alias.query.filter_by(name="alias-False").first()
            server = Server.query.filter_by(name="server-False").first()
            variable = Variable.query.filter_by(name="variable-False").first()
            secret = Secret.query.filter_by(name="secret-False").first()

            self.assertIsNotNone(alias)
            self.assertIsNotNone(server)
            self.assertIsNotNone(variable)
            self.assertIsNotNone(secret)

            self.assertFalse(alias.enabled, "Alias should be disabled in DB")
            self.assertFalse(server.enabled, "Server should be disabled in DB")
            self.assertFalse(variable.enabled, "Variable should be disabled in DB")
            self.assertFalse(secret.enabled, "Secret should be disabled in DB")

    def test_entities_enabled_field_after_session_refresh(self):
        """Test that enabled field persists correctly after session refresh."""
        self._create_test_entities(enabled_state=False)

        with self.app.app_context():
            # Query once
            alias1 = Alias.query.filter_by(name="alias-False").first()
            self.assertFalse(alias1.enabled, "First query should show disabled")

            # Close session and query again
            db.session.close()

            # Query again in fresh session
            alias2 = Alias.query.filter_by(name="alias-False").first()
            self.assertFalse(alias2.enabled, "Second query should show disabled")

    def test_filter_disabled_entities_for_export(self):
        """Test that we can filter and retrieve only disabled entities."""
        # Create mix of enabled and disabled
        self._create_test_entities(enabled_state=True)
        self._create_test_entities(enabled_state=False)

        with self.app.app_context():
            # Filter for disabled only
            disabled_aliases = Alias.query.filter_by(enabled=False).all()
            disabled_servers = Server.query.filter_by(enabled=False).all()
            disabled_variables = Variable.query.filter_by(enabled=False).all()
            disabled_secrets = Secret.query.filter_by(enabled=False).all()

            # Should find exactly one of each
            self.assertEqual(len(disabled_aliases), 1)
            self.assertEqual(len(disabled_servers), 1)
            self.assertEqual(len(disabled_variables), 1)
            self.assertEqual(len(disabled_secrets), 1)

            # Verify they are the correct ones
            self.assertEqual(disabled_aliases[0].name, "alias-False")
            self.assertEqual(disabled_servers[0].name, "server-False")
            self.assertEqual(disabled_variables[0].name, "variable-False")
            self.assertEqual(disabled_secrets[0].name, "secret-False")


if __name__ == "__main__":
    unittest.main()
