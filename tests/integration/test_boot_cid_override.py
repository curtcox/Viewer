"""Integration tests for Boot CID Override functionality.

These tests verify that when a boot CID is imported, it correctly overrides
existing data in the database. This is critical for ensuring consistent
behavior where boot CID data takes precedence over pre-existing data.

The override behavior follows upsert semantics:
- If an entity with the same name exists, it is updated
- If no entity with the same name exists, it is created
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import create_app, db
from boot_cid_importer import import_boot_cid
from cid_utils import generate_cid
from db_access import create_cid_record
from models import Alias, Server, Variable

pytestmark = pytest.mark.integration


class TestBootCidOverride:
    """Integration tests for boot CID override functionality.

    These tests verify that boot CID imports correctly override
    pre-existing data in the database with the same entity names.
    """

    CLI_ROOT = Path(__file__).parent.parent.parent

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with isolated database."""
        self.app = create_app(
            {  # pylint: disable=attribute-defined-outside-init
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
            }
        )

        with self.app.app_context():
            db.create_all()

        yield

        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_boot_cid_with_aliases(self, aliases_data: list[dict]) -> str:
        """Create a boot CID containing aliases and return its CID value.

        Args:
            aliases_data: List of alias dictionaries with 'name' and 'definition'

        Returns:
            The generated boot CID value
        """
        aliases_content = json.dumps(aliases_data).encode("utf-8")
        aliases_cid = generate_cid(aliases_content)
        create_cid_record(aliases_cid, aliases_content)

        payload_data = {
            "version": 6,
            "aliases": aliases_cid,
        }
        content = json.dumps(payload_data).encode("utf-8")
        boot_cid = generate_cid(content)
        create_cid_record(boot_cid, content)

        return boot_cid

    def _create_boot_cid_with_servers(self, servers_data: list[dict]) -> str:
        """Create a boot CID containing servers and return its CID value.

        Args:
            servers_data: List of server dictionaries with 'name' and 'definition'

        Returns:
            The generated boot CID value
        """
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

        return boot_cid

    def _create_boot_cid_with_variables(self, variables_data: list[dict]) -> str:
        """Create a boot CID containing variables and return its CID value.

        Args:
            variables_data: List of variable dictionaries with 'name' and 'definition'

        Returns:
            The generated boot CID value
        """
        variables_content = json.dumps(variables_data).encode("utf-8")
        variables_cid = generate_cid(variables_content)
        create_cid_record(variables_cid, variables_content)

        payload_data = {
            "version": 6,
            "variables": variables_cid,
        }
        content = json.dumps(payload_data).encode("utf-8")
        boot_cid = generate_cid(content)
        create_cid_record(boot_cid, content)

        return boot_cid

    def _create_boot_cid_with_multiple_entities(
        self,
        aliases_data: list[dict] | None = None,
        servers_data: list[dict] | None = None,
        variables_data: list[dict] | None = None,
    ) -> str:
        """Create a boot CID containing multiple entity types.

        Args:
            aliases_data: Optional list of alias dictionaries
            servers_data: Optional list of server dictionaries
            variables_data: Optional list of variable dictionaries

        Returns:
            The generated boot CID value
        """
        payload_data: dict = {"version": 6}

        if aliases_data:
            aliases_content = json.dumps(aliases_data).encode("utf-8")
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)
            payload_data["aliases"] = aliases_cid

        if servers_data:
            servers_content = json.dumps(servers_data).encode("utf-8")
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)
            payload_data["servers"] = servers_cid

        if variables_data:
            variables_content = json.dumps(variables_data).encode("utf-8")
            variables_cid = generate_cid(variables_content)
            create_cid_record(variables_cid, variables_content)
            payload_data["variables"] = variables_cid

        content = json.dumps(payload_data).encode("utf-8")
        boot_cid = generate_cid(content)
        create_cid_record(boot_cid, content)

        return boot_cid

    def test_boot_cid_overrides_existing_server(self):
        """Test that boot CID data overrides a pre-existing server with the same name.

        Expected behavior:
        - Create a server with name 'test-server' and definition 'original'
        - Import boot CID with a server named 'test-server' with definition 'overridden'
        - The server's definition should now be 'overridden'

        This verifies that boot CID import uses upsert semantics for servers.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing server in database
            original_server = Server(
                name="test-server",
                definition='def main():\n    return "original response"',
                enabled=True,
            )
            db.session.add(original_server)
            db.session.commit()

            # Verify the original server exists
            server = Server.query.filter_by(name="test-server").first()
            assert server is not None
            assert "original response" in server.definition

            # Step 2: Create boot CID with conflicting server definition
            servers_data = [
                {
                    "name": "test-server",
                    "definition": 'def main():\n    return "overridden response"',
                }
            ]
            boot_cid = self._create_boot_cid_with_servers(servers_data)

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify the server definition was overridden
            server = Server.query.filter_by(name="test-server").first()
            assert server is not None, "Server should still exist after import"
            assert "overridden response" in server.definition, (
                f"Server definition should be overridden. Got: {server.definition}"
            )
            assert "original response" not in server.definition, (
                "Original definition should be replaced"
            )

    def test_boot_cid_overrides_existing_alias(self):
        """Test that boot CID data overrides a pre-existing alias with the same name.

        Expected behavior:
        - Create an alias with name 'test-alias' pointing to '/original-target'
        - Import boot CID with an alias named 'test-alias' pointing to '/overridden-target'
        - The alias should now point to '/overridden-target'

        This verifies that boot CID import uses upsert semantics for aliases.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing alias in database
            original_alias = Alias(
                name="test-alias",
                definition="/test-alias -> /original-target",
                enabled=True,
            )
            db.session.add(original_alias)
            db.session.commit()

            # Verify the original alias exists
            alias = Alias.query.filter_by(name="test-alias").first()
            assert alias is not None
            assert "/original-target" in alias.definition

            # Step 2: Create boot CID with conflicting alias definition
            aliases_data = [
                {
                    "name": "test-alias",
                    "definition": "/test-alias -> /overridden-target",
                }
            ]
            boot_cid = self._create_boot_cid_with_aliases(aliases_data)

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify the alias definition was overridden
            alias = Alias.query.filter_by(name="test-alias").first()
            assert alias is not None, "Alias should still exist after import"
            assert "/overridden-target" in alias.definition, (
                f"Alias definition should be overridden. Got: {alias.definition}"
            )
            assert "/original-target" not in alias.definition, (
                "Original definition should be replaced"
            )

    def test_boot_cid_overrides_existing_variable(self):
        """Test that boot CID data overrides a pre-existing variable with the same name.

        Expected behavior:
        - Create a variable with name 'test-variable' and value 'original_value'
        - Import boot CID with a variable named 'test-variable' with value 'overridden_value'
        - The variable's value should now be 'overridden_value'

        This verifies that boot CID import uses upsert semantics for variables.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing variable in database
            original_variable = Variable(
                name="test-variable",
                definition="original_value",
            )
            db.session.add(original_variable)
            db.session.commit()

            # Verify the original variable exists
            variable = Variable.query.filter_by(name="test-variable").first()
            assert variable is not None
            assert variable.definition == "original_value"

            # Step 2: Create boot CID with conflicting variable definition
            variables_data = [
                {
                    "name": "test-variable",
                    "definition": "overridden_value",
                }
            ]
            boot_cid = self._create_boot_cid_with_variables(variables_data)

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify the variable definition was overridden
            variable = Variable.query.filter_by(name="test-variable").first()
            assert variable is not None, "Variable should still exist after import"
            assert variable.definition == "overridden_value", (
                f"Variable definition should be overridden. Got: {variable.definition}"
            )

    def test_boot_cid_overrides_multiple_entity_types(self):
        """Test that boot CID can override multiple entity types simultaneously.

        Expected behavior:
        - Create pre-existing server, alias, and variable with original values
        - Import boot CID with conflicting definitions for all three
        - All three entities should be updated to the new values

        This verifies that boot CID import handles multiple entity types in one import.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing entities in database
            original_server = Server(
                name="multi-test-server",
                definition='def main():\n    return "original server"',
                enabled=True,
            )
            original_alias = Alias(
                name="multi-test-alias",
                definition="/multi-test-alias -> /original-alias-target",
                enabled=True,
            )
            original_variable = Variable(
                name="multi-test-variable",
                definition="original_variable_value",
            )
            db.session.add(original_server)
            db.session.add(original_alias)
            db.session.add(original_variable)
            db.session.commit()

            # Verify originals exist
            assert Server.query.filter_by(name="multi-test-server").first() is not None
            assert Alias.query.filter_by(name="multi-test-alias").first() is not None
            assert (
                Variable.query.filter_by(name="multi-test-variable").first() is not None
            )

            # Step 2: Create boot CID with conflicting definitions for all types
            boot_cid = self._create_boot_cid_with_multiple_entities(
                aliases_data=[
                    {
                        "name": "multi-test-alias",
                        "definition": "/multi-test-alias -> /overridden-alias-target",
                    }
                ],
                servers_data=[
                    {
                        "name": "multi-test-server",
                        "definition": 'def main():\n    return "overridden server"',
                    }
                ],
                variables_data=[
                    {
                        "name": "multi-test-variable",
                        "definition": "overridden_variable_value",
                    }
                ],
            )

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify all entities were overridden
            server = Server.query.filter_by(name="multi-test-server").first()
            assert server is not None
            assert "overridden server" in server.definition, (
                f"Server should be overridden. Got: {server.definition}"
            )

            alias = Alias.query.filter_by(name="multi-test-alias").first()
            assert alias is not None
            assert "/overridden-alias-target" in alias.definition, (
                f"Alias should be overridden. Got: {alias.definition}"
            )

            variable = Variable.query.filter_by(name="multi-test-variable").first()
            assert variable is not None
            assert variable.definition == "overridden_variable_value", (
                f"Variable should be overridden. Got: {variable.definition}"
            )

    def test_boot_cid_override_preserves_non_conflicting_entities(self):
        """Test that boot CID import does not affect entities with different names.

        Expected behavior:
        - Create pre-existing entities (server, alias, variable) with unique names
        - Import boot CID with different entity names
        - Original entities should remain unchanged
        - New entities from boot CID should be created

        This verifies that boot CID import only affects entities with matching names.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing entities that should NOT be affected
            preserved_server = Server(
                name="preserved-server",
                definition='def main():\n    return "preserved server response"',
                enabled=True,
            )
            preserved_alias = Alias(
                name="preserved-alias",
                definition="/preserved-alias -> /preserved-target",
                enabled=True,
            )
            preserved_variable = Variable(
                name="preserved-variable",
                definition="preserved_value",
            )
            db.session.add(preserved_server)
            db.session.add(preserved_alias)
            db.session.add(preserved_variable)
            db.session.commit()

            # Step 2: Create boot CID with DIFFERENT entity names
            boot_cid = self._create_boot_cid_with_multiple_entities(
                aliases_data=[
                    {
                        "name": "new-boot-alias",
                        "definition": "/new-boot-alias -> /new-target",
                    }
                ],
                servers_data=[
                    {
                        "name": "new-boot-server",
                        "definition": 'def main():\n    return "new boot server"',
                    }
                ],
                variables_data=[
                    {
                        "name": "new-boot-variable",
                        "definition": "new_boot_value",
                    }
                ],
            )

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify original entities are PRESERVED (unchanged)
            server = Server.query.filter_by(name="preserved-server").first()
            assert server is not None, "Preserved server should still exist"
            assert "preserved server response" in server.definition, (
                "Preserved server definition should not change"
            )

            alias = Alias.query.filter_by(name="preserved-alias").first()
            assert alias is not None, "Preserved alias should still exist"
            assert "/preserved-target" in alias.definition, (
                "Preserved alias definition should not change"
            )

            variable = Variable.query.filter_by(name="preserved-variable").first()
            assert variable is not None, "Preserved variable should still exist"
            assert variable.definition == "preserved_value", (
                "Preserved variable definition should not change"
            )

            # Step 5: Verify new entities from boot CID were CREATED
            new_server = Server.query.filter_by(name="new-boot-server").first()
            assert new_server is not None, "New boot server should be created"
            assert "new boot server" in new_server.definition

            new_alias = Alias.query.filter_by(name="new-boot-alias").first()
            assert new_alias is not None, "New boot alias should be created"
            assert "/new-target" in new_alias.definition

            new_variable = Variable.query.filter_by(name="new-boot-variable").first()
            assert new_variable is not None, "New boot variable should be created"
            assert new_variable.definition == "new_boot_value"

    def test_boot_cid_override_updates_enabled_status(self):
        """Test that boot CID can override the enabled status of entities.

        Expected behavior:
        - Create a pre-existing enabled server
        - Import boot CID with the same server but disabled
        - The server should now be disabled

        This verifies that boot CID import correctly handles the enabled field.
        """
        with self.app.app_context():
            # Step 1: Create pre-existing ENABLED server
            original_server = Server(
                name="enabled-status-server",
                definition='def main():\n    return "status test"',
                enabled=True,
            )
            db.session.add(original_server)
            db.session.commit()

            # Verify it's enabled
            server = Server.query.filter_by(name="enabled-status-server").first()
            assert server.enabled is True

            # Step 2: Create boot CID with server set to DISABLED
            servers_content = json.dumps(
                [
                    {
                        "name": "enabled-status-server",
                        "definition": 'def main():\n    return "status test updated"',
                        "enabled": False,
                    }
                ]
            ).encode("utf-8")
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            payload_data = {
                "version": 6,
                "servers": servers_cid,
            }
            content = json.dumps(payload_data).encode("utf-8")
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

            # Step 3: Import the boot CID
            success, error = import_boot_cid(self.app, boot_cid)
            assert success, f"Boot CID import failed: {error}"

            # Step 4: Verify the enabled status was overridden
            server = Server.query.filter_by(name="enabled-status-server").first()
            assert server is not None
            assert server.enabled is False, (
                f"Server enabled status should be overridden to False. Got: {server.enabled}"
            )


class TestBootCidOverrideCLI:
    """Integration tests for boot CID override via CLI.

    These tests verify that boot CID override works consistently whether
    the import is performed via the CLI or via direct API calls.
    """

    CLI_ROOT = Path(__file__).parent.parent.parent

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with isolated database."""
        self.tmp_path = tmp_path  # pylint: disable=attribute-defined-outside-init
        self.app = create_app(
            {  # pylint: disable=attribute-defined-outside-init
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
                "WTF_CSRF_ENABLED": False,
            }
        )

        with self.app.app_context():
            db.create_all()

        yield

        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_cli_boot_cid_override_produces_same_result(self):
        """Test that CLI boot CID override produces same result as direct API import.

        Expected behavior:
        - Create CID files in cids directory
        - Run CLI with boot CID argument
        - Query /servers.json to verify the overridden data is present

        This verifies that the CLI interface correctly triggers boot CID override.
        """
        # Create server content for boot CID
        servers_data = [
            {
                "name": "cli-override-test-server",
                "definition": 'def main():\n    return "cli override test"',
            }
        ]
        servers_content = json.dumps(servers_data).encode("utf-8")
        servers_cid = generate_cid(servers_content)

        # Store in cids directory
        servers_cid_file = self.CLI_ROOT / "cids" / servers_cid
        servers_cid_file.write_bytes(servers_content)

        try:
            # Create boot CID
            boot_payload = {
                "version": 6,
                "servers": servers_cid,
            }
            boot_content = json.dumps(boot_payload).encode("utf-8")
            boot_cid = generate_cid(boot_content)

            # Store boot CID in cids directory
            boot_cid_file = self.CLI_ROOT / "cids" / boot_cid
            boot_cid_file.write_bytes(boot_content)

            try:
                # Run CLI with boot CID and query servers
                env = os.environ.copy()
                env.pop("TESTING", None)

                result = subprocess.run(
                    [
                        sys.executable,
                        "main.py",
                        "--in-memory-db",
                        "/servers.json",
                        boot_cid,
                    ],
                    cwd=self.CLI_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                    env=env,
                )

                # Should succeed
                assert "Status: 200" in result.stdout, (
                    f"Expected 200 status. stdout: {result.stdout}, stderr: {result.stderr}"
                )

                # Parse response
                lines = result.stdout.splitlines()
                json_start = next(
                    i for i, line in enumerate(lines) if line.startswith("[")
                )
                json_text = "\n".join(lines[json_start:])

                servers = json.loads(json_text)

                # Should include the server from boot CID
                server_names = [s["name"] for s in servers]
                assert "cli-override-test-server" in server_names, (
                    f"Boot server not found in: {server_names}"
                )

            finally:
                if boot_cid_file.exists():
                    boot_cid_file.unlink()

        finally:
            if servers_cid_file.exists():
                servers_cid_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
