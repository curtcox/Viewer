"""Integration tests for boot image with dynamically added content.

These tests verify that when adding aliases, servers, variables, and templates
to boot.source.json or templates.source.json, the generated boot image contains
the expected content and functions correctly after import.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Dict

import pytest

import main
from app import create_app, db
from db_access import create_cid_record
from db_access.cids import get_cid_by_path
from generate_boot_image import BootImageGenerator
from models import Alias, Server, Variable
from template_manager import (
    get_template_by_key,
    get_templates_config,
    resolve_cid_value,
)

pytestmark = pytest.mark.integration


class TestBootImageDynamicContent:
    """Integration tests for boot image with dynamically added content."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with isolated project directory."""
        # Create app with test configuration
        self.app = create_app({  # pylint: disable=attribute-defined-outside-init
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/test.db',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            db.create_all()

        # Monkeypatch main.app so handle_boot_cid_import uses our test app
        original_app = main.app
        main.app = self.app

        # Create an isolated project directory for testing
        self.project_dir = tmp_path / "project"  # pylint: disable=attribute-defined-outside-init
        self._create_test_project_structure()

        yield

        # Restore original app
        main.app = original_app

        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_test_project_structure(self):
        """Create a minimal project structure for testing."""
        # Create directories
        ref_templates = self.project_dir / "reference_templates"
        ref_templates.mkdir(parents=True)
        (ref_templates / "aliases").mkdir()
        (ref_templates / "variables").mkdir()
        (ref_templates / "servers" / "definitions").mkdir(parents=True)
        (ref_templates / "uploads" / "contents").mkdir(parents=True)
        (self.project_dir / "cids").mkdir()

        # Create base boot source files (minimal, default, and legacy boot)
        boot_source = {
            "version": 6,
            "runtime": '{"python": {"version": "3.11.0"}}',
            "project_files": "{}",
            "aliases": [],
            "servers": [],
            "variables": [
                {
                    "name": "templates",
                    "definition": "GENERATED:templates.json",
                    "enabled": True
                }
            ]
        }
        boot_source_json = json.dumps(boot_source, indent=2)
        (ref_templates / "boot.source.json").write_text(boot_source_json)
        (ref_templates / "minimal.boot.source.json").write_text(boot_source_json)
        (ref_templates / "default.boot.source.json").write_text(boot_source_json)

        # Create base templates.source.json
        templates_source = {
            "aliases": {},
            "servers": {},
            "variables": {},
            "secrets": {},
            "uploads": {}
        }
        (ref_templates / "templates.source.json").write_text(
            json.dumps(templates_source, indent=2)
        )

        # Create base uis.source.json so UI content generation succeeds
        uis_source = {"aliases": {}, "servers": {}, "variables": {}}
        (ref_templates / "uis.source.json").write_text(json.dumps(uis_source, indent=2))

    def _add_alias_to_boot_source(self, name: str, definition_content: str) -> str:
        """Add an alias to boot.source.json."""
        ref_templates = self.project_dir / "reference_templates"

        # Create alias definition file
        alias_file = ref_templates / "aliases" / f"{name}.txt"
        alias_file.write_text(definition_content)
        rel_path = f"reference_templates/aliases/{name}.txt"

        # Update boot.source.json
        boot_source_file = ref_templates / "boot.source.json"
        boot_source = json.loads(boot_source_file.read_text())
        boot_source["aliases"].append({
            "name": name,
            "definition_cid": rel_path,
            "enabled": True
        })
        boot_source_file.write_text(json.dumps(boot_source, indent=2))

        return rel_path

    def _add_server_to_boot_source(
        self,
        name: str,
        definition_content: str
    ) -> str:
        """Add a server to boot.source.json.

        Args:
            name: Server name
            definition_content: Python code for the server

        Returns:
            The relative path to the definition file
        """
        ref_templates = self.project_dir / "reference_templates"

        # Create server definition file
        server_file = ref_templates / "servers" / "definitions" / f"{name}.py"
        server_file.write_text(definition_content)
        rel_path = f"reference_templates/servers/definitions/{name}.py"

        # Update boot.source.json
        boot_source_file = ref_templates / "boot.source.json"
        boot_source = json.loads(boot_source_file.read_text())
        boot_source["servers"].append({
            "name": name,
            "definition_cid": rel_path,
            "enabled": True
        })
        boot_source_file.write_text(json.dumps(boot_source, indent=2))

        return rel_path

    def _add_variable_to_boot_source(
        self,
        name: str,
        definition: str
    ):
        """Add a variable to boot.source.json.

        Args:
            name: Variable name
            definition: Variable definition value
        """
        ref_templates = self.project_dir / "reference_templates"

        # Update boot.source.json
        boot_source_file = ref_templates / "boot.source.json"
        boot_source = json.loads(boot_source_file.read_text())
        boot_source["variables"].append({
            "name": name,
            "definition": definition,
            "enabled": True
        })
        boot_source_file.write_text(json.dumps(boot_source, indent=2))

    def _add_alias_template_to_templates_source(
        self,
        key: str,
        name: str,
        description: str,
        definition_content: str
    ) -> str:
        """Add an alias template to templates.source.json.

        Args:
            key: Template key
            name: Template display name
            description: Template description
            definition_content: Content for the alias definition

        Returns:
            The relative path to the definition file
        """
        ref_templates = self.project_dir / "reference_templates"

        # Create alias definition file
        alias_file = ref_templates / "aliases" / f"template_{key}.txt"
        alias_file.write_text(definition_content)
        rel_path = f"reference_templates/aliases/template_{key}.txt"

        # Update templates.source.json
        templates_source_file = ref_templates / "templates.source.json"
        templates_source = json.loads(templates_source_file.read_text())
        templates_source["aliases"][key] = {
            "name": name,
            "description": description,
            "definition_cid": rel_path
        }
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        return rel_path

    def _add_server_template_to_templates_source(
        self,
        key: str,
        name: str,
        description: str,
        definition_content: str
    ) -> str:
        """Add a server template to templates.source.json.

        Args:
            key: Template key
            name: Template display name
            description: Template description
            definition_content: Python code for the server

        Returns:
            The relative path to the definition file
        """
        ref_templates = self.project_dir / "reference_templates"

        # Create server definition file
        server_file = ref_templates / "servers" / "definitions" / f"template_{key}.py"
        server_file.write_text(definition_content)
        rel_path = f"reference_templates/servers/definitions/template_{key}.py"

        # Update templates.source.json
        templates_source_file = ref_templates / "templates.source.json"
        templates_source = json.loads(templates_source_file.read_text())
        templates_source["servers"][key] = {
            "name": name,
            "description": description,
            "definition_cid": rel_path
        }
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        return rel_path

    def _add_variable_template_to_templates_source(
        self,
        key: str,
        name: str,
        description: str,
        definition_content: str
    ) -> str:
        """Add a variable template to templates.source.json.

        Args:
            key: Template key
            name: Template display name
            description: Template description
            definition_content: Content for the variable definition

        Returns:
            The relative path to the definition file
        """
        ref_templates = self.project_dir / "reference_templates"

        # Create variable definition file
        var_file = ref_templates / "variables" / f"template_{key}.txt"
        var_file.write_text(definition_content)
        rel_path = f"reference_templates/variables/template_{key}.txt"

        # Update templates.source.json
        templates_source_file = ref_templates / "templates.source.json"
        templates_source = json.loads(templates_source_file.read_text())
        templates_source["variables"][key] = {
            "name": name,
            "description": description,
            "definition_cid": rel_path
        }
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        return rel_path

    def _add_upload_template_to_templates_source(
        self,
        key: str,
        name: str,
        description: str,
        content: str
    ) -> str:
        """Add an upload template to templates.source.json.

        Args:
            key: Template key
            name: Template display name
            description: Template description
            content: Content for the upload file

        Returns:
            The relative path to the content file
        """
        ref_templates = self.project_dir / "reference_templates"

        # Create upload content file
        upload_file = ref_templates / "uploads" / "contents" / f"template_{key}.html"
        upload_file.write_text(content)
        rel_path = f"reference_templates/uploads/contents/template_{key}.html"

        # Update templates.source.json
        templates_source_file = ref_templates / "templates.source.json"
        templates_source = json.loads(templates_source_file.read_text())
        templates_source["uploads"][key] = {
            "name": name,
            "description": description,
            "content_cid": rel_path
        }
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        return rel_path

    def _generate_and_import_boot_image(self) -> Dict[str, str]:
        """Generate boot image and import it.

        Returns:
            Dictionary with 'templates_cid' and 'boot_cid' keys
        """
        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        result = generator.generate()

        # Load all CIDs into database
        with self.app.app_context():
            cids_dir = generator.cids_dir
            for cid_file in cids_dir.iterdir():
                if cid_file.is_file():
                    cid = cid_file.name
                    path = f"/{cid}"

                    # Skip if CID already exists in database
                    if get_cid_by_path(path):
                        continue

                    content = cid_file.read_bytes()
                    create_cid_record(cid, content)

        # Import boot CID
        from contextlib import redirect_stdout
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            main.handle_boot_cid_import(result['boot_cid'])

        return result

    # --- Tests for Adding Aliases to boot.source.json ---

    def test_added_alias_is_in_boot_image(self):
        """Test that an alias added to boot.source.json is in the generated boot image."""
        # Add an alias to boot.source.json
        self._add_alias_to_boot_source(
            "test-alias",
            "literal /test-alias -> /test-target"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated boot.json
        boot_json_path = self.project_dir / "reference_templates" / "boot.json"
        boot_data = json.loads(boot_json_path.read_text())

        # Verify the alias is in the boot image
        assert len(boot_data["aliases"]) == 1
        assert boot_data["aliases"][0]["name"] == "test-alias"
        # The definition_cid should now be a CID, not the file path
        assert not boot_data["aliases"][0]["definition_cid"].startswith("reference_templates/")

    def test_boot_cid_loads_added_alias(self):
        """Test that booting with CID shows the added alias in /aliases."""
        # Add an alias to boot.source.json
        self._add_alias_to_boot_source(
            "dynamic-alias",
            "literal /dynamic -> /dynamic-target"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify alias is accessible
        with self.app.app_context():
            alias = Alias.query.filter_by(name='dynamic-alias').first()
            assert alias is not None, "Alias should be loaded from boot image"
            assert alias.enabled is True

    def test_loaded_alias_functions_correctly(self):
        """Test that the loaded alias works as expected."""
        # Add an alias to boot.source.json
        self._add_alias_to_boot_source(
            "functional-alias",
            "literal /func-alias -> /func-target"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify alias definition is correct
        with self.app.app_context():
            alias = Alias.query.filter_by(name='functional-alias').first()
            assert alias is not None
            assert "literal /func-alias -> /func-target" in alias.definition
            assert alias.target_path == "/func-target"

    # --- Tests for Adding Servers to boot.source.json ---

    def test_added_server_is_in_boot_image(self):
        """Test that a server added to boot.source.json is in the generated boot image."""
        # Add a server to boot.source.json
        self._add_server_to_boot_source(
            "test-server",
            "def main(context):\n    return 'Hello from test server'\n"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated boot.json
        boot_json_path = self.project_dir / "reference_templates" / "boot.json"
        boot_data = json.loads(boot_json_path.read_text())

        # Verify the server is in the boot image
        assert len(boot_data["servers"]) == 1
        assert boot_data["servers"][0]["name"] == "test-server"
        # The definition_cid should now be a CID, not the file path
        assert not boot_data["servers"][0]["definition_cid"].startswith("reference_templates/")

    def test_boot_cid_loads_added_server(self):
        """Test that booting with CID shows the added server in /servers."""
        # Add a server to boot.source.json
        self._add_server_to_boot_source(
            "dynamic-server",
            "def main(context):\n    return 'Dynamic server response'\n"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify server is accessible
        with self.app.app_context():
            server = Server.query.filter_by(name='dynamic-server').first()
            assert server is not None, "Server should be loaded from boot image"
            assert server.enabled is True

    def test_loaded_server_functions_correctly(self):
        """Test that the loaded server has the correct definition."""
        # Add a server to boot.source.json
        server_code = "def main(context):\n    return 'Functional server output'\n"
        self._add_server_to_boot_source("functional-server", server_code)

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify server definition is correct
        with self.app.app_context():
            server = Server.query.filter_by(name='functional-server').first()
            assert server is not None
            assert "def main(context):" in server.definition
            assert "Functional server output" in server.definition

    # --- Tests for Adding Variables to boot.source.json ---

    def test_added_variable_is_in_boot_image(self):
        """Test that a variable added to boot.source.json is in the generated boot image."""
        # Add a variable to boot.source.json
        self._add_variable_to_boot_source("test-var", "test-value-123")

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated boot.json
        boot_json_path = self.project_dir / "reference_templates" / "boot.json"
        boot_data = json.loads(boot_json_path.read_text())

        # Verify the variable is in the boot image
        var_names = [v["name"] for v in boot_data["variables"]]
        assert "test-var" in var_names
        # Find the variable
        test_var = next(v for v in boot_data["variables"] if v["name"] == "test-var")
        assert test_var["definition"] == "test-value-123"

    def test_boot_cid_loads_added_variable(self):
        """Test that booting with CID shows the added variable in /variables."""
        # Add a variable to boot.source.json
        self._add_variable_to_boot_source("dynamic-var", "dynamic-value")

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify variable is accessible
        with self.app.app_context():
            var = Variable.query.filter_by(name='dynamic-var').first()
            assert var is not None, "Variable should be loaded from boot image"
            assert var.enabled is True

    def test_loaded_variable_functions_correctly(self):
        """Test that the loaded variable works as expected."""
        # Add a variable to boot.source.json
        self._add_variable_to_boot_source("functional-var", "functional-value-456")

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify variable definition is correct
        with self.app.app_context():
            var = Variable.query.filter_by(name='functional-var').first()
            assert var is not None
            assert var.definition == "functional-value-456"

    # --- Tests for Adding Alias Templates to templates.source.json ---

    def test_added_alias_template_is_in_boot_image(self):
        """Test that an alias template added to templates.source.json is in the boot image."""
        # Add an alias template
        self._add_alias_template_to_templates_source(
            "custom-alias-template",
            "Custom Alias Template",
            "A custom alias template for testing",
            "literal /custom -> /custom-target"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated templates.json
        templates_json_path = self.project_dir / "reference_templates" / "templates.json"
        templates_data = json.loads(templates_json_path.read_text())

        # Verify the alias template is in templates.json
        assert "custom-alias-template" in templates_data["aliases"]
        assert templates_data["aliases"]["custom-alias-template"]["name"] == "Custom Alias Template"

    def test_boot_cid_shows_alias_template_in_variables_templates(self):
        """Test that booting with CID includes the alias template in /variables/templates."""
        # Add an alias template
        self._add_alias_template_to_templates_source(
            "accessible-alias-template",
            "Accessible Alias",
            "An accessible alias template",
            "literal /accessible -> /accessible-target"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is accessible
        with self.app.app_context():
            templates_config = get_templates_config()
            assert templates_config is not None
            assert "accessible-alias-template" in templates_config["aliases"]

    def test_loaded_alias_template_can_be_used(self):
        """Test that the user can use the alias template to create a new alias."""
        # Add an alias template
        self._add_alias_template_to_templates_source(
            "usable-alias-template",
            "Usable Alias Template",
            "A usable alias template",
            "literal /usable -> /usable-target"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is usable
        with self.app.app_context():
            template = get_template_by_key("aliases", "usable-alias-template")
            assert template is not None
            assert template["name"] == "Usable Alias Template"
            assert "definition_cid" in template

            # The definition should be resolvable
            definition = resolve_cid_value(template["definition_cid"])
            assert definition is not None
            assert "literal /usable -> /usable-target" in definition

    def test_alias_from_template_functions_correctly(self):
        """Test that an alias created from the template functions as expected."""
        # Add an alias template with specific definition
        self._add_alias_template_to_templates_source(
            "working-alias-template",
            "Working Alias",
            "A working alias template",
            "literal /working -> /working-result"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Get template definition
        with self.app.app_context():
            template = get_template_by_key("aliases", "working-alias-template")
            definition = resolve_cid_value(template["definition_cid"])

            # Create an alias using the template definition
            alias = Alias(
                name="from-template",
                definition=definition,
                enabled=True
            )
            db.session.add(alias)
            db.session.commit()

            # Verify the alias works
            created_alias = Alias.query.filter_by(name="from-template").first()
            assert created_alias is not None
            assert created_alias.target_path == "/working-result"

    # --- Tests for Adding Server Templates to templates.source.json ---

    def test_added_server_template_is_in_boot_image(self):
        """Test that a server template added to templates.source.json is in the boot image."""
        # Add a server template
        self._add_server_template_to_templates_source(
            "custom-server-template",
            "Custom Server Template",
            "A custom server template for testing",
            "def main(context):\n    return 'Custom server response'\n"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated templates.json
        templates_json_path = self.project_dir / "reference_templates" / "templates.json"
        templates_data = json.loads(templates_json_path.read_text())

        # Verify the server template is in templates.json
        assert "custom-server-template" in templates_data["servers"]
        assert templates_data["servers"]["custom-server-template"]["name"] == "Custom Server Template"

    def test_boot_cid_shows_server_template_in_variables_templates(self):
        """Test that booting with CID includes the server template in /variables/templates."""
        # Add a server template
        self._add_server_template_to_templates_source(
            "accessible-server-template",
            "Accessible Server",
            "An accessible server template",
            "def main(context):\n    return 'Accessible'\n"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is accessible
        with self.app.app_context():
            templates_config = get_templates_config()
            assert templates_config is not None
            assert "accessible-server-template" in templates_config["servers"]

    def test_loaded_server_template_can_be_used(self):
        """Test that the user can use the server template to create a new server."""
        # Add a server template
        self._add_server_template_to_templates_source(
            "usable-server-template",
            "Usable Server Template",
            "A usable server template",
            "def main(context):\n    return 'Usable server'\n"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is usable
        with self.app.app_context():
            template = get_template_by_key("servers", "usable-server-template")
            assert template is not None
            assert template["name"] == "Usable Server Template"
            assert "definition_cid" in template

            # The definition should be resolvable
            definition = resolve_cid_value(template["definition_cid"])
            assert definition is not None
            assert "def main(context):" in definition

    def test_server_from_template_functions_correctly(self):
        """Test that a server created from the template functions as expected."""
        # Add a server template with specific definition
        self._add_server_template_to_templates_source(
            "working-server-template",
            "Working Server",
            "A working server template",
            "def main(context):\n    return 'Working server output'\n"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Get template definition
        with self.app.app_context():
            template = get_template_by_key("servers", "working-server-template")
            definition = resolve_cid_value(template["definition_cid"])

            # Create a server using the template definition
            server = Server(
                name="from-server-template",
                definition=definition,
                enabled=True
            )
            db.session.add(server)
            db.session.commit()

            # Verify the server works
            created_server = Server.query.filter_by(name="from-server-template").first()
            assert created_server is not None
            assert "Working server output" in created_server.definition

    # --- Tests for Adding Variable Templates to templates.source.json ---

    def test_added_variable_template_is_in_boot_image(self):
        """Test that a variable template added to templates.source.json is in the boot image."""
        # Add a variable template
        self._add_variable_template_to_templates_source(
            "custom-var-template",
            "Custom Variable Template",
            "A custom variable template for testing",
            "custom-variable-value"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated templates.json
        templates_json_path = self.project_dir / "reference_templates" / "templates.json"
        templates_data = json.loads(templates_json_path.read_text())

        # Verify the variable template is in templates.json
        assert "custom-var-template" in templates_data["variables"]
        assert templates_data["variables"]["custom-var-template"]["name"] == "Custom Variable Template"

    def test_boot_cid_shows_variable_template_in_variables_templates(self):
        """Test that booting with CID includes the variable template in /variables/templates."""
        # Add a variable template
        self._add_variable_template_to_templates_source(
            "accessible-var-template",
            "Accessible Variable",
            "An accessible variable template",
            "accessible-var-value"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is accessible
        with self.app.app_context():
            templates_config = get_templates_config()
            assert templates_config is not None
            assert "accessible-var-template" in templates_config["variables"]

    def test_loaded_variable_template_can_be_used(self):
        """Test that the user can use the variable template to create a new variable."""
        # Add a variable template
        self._add_variable_template_to_templates_source(
            "usable-var-template",
            "Usable Variable Template",
            "A usable variable template",
            "usable-variable-value"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is usable
        with self.app.app_context():
            template = get_template_by_key("variables", "usable-var-template")
            assert template is not None
            assert template["name"] == "Usable Variable Template"
            assert "definition_cid" in template

            # The definition should be resolvable
            definition = resolve_cid_value(template["definition_cid"])
            assert definition is not None
            assert "usable-variable-value" in definition

    def test_variable_from_template_functions_correctly(self):
        """Test that a variable created from the template functions as expected."""
        # Add a variable template with specific definition
        self._add_variable_template_to_templates_source(
            "working-var-template",
            "Working Variable",
            "A working variable template",
            "working-variable-content"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Get template definition
        with self.app.app_context():
            template = get_template_by_key("variables", "working-var-template")
            definition = resolve_cid_value(template["definition_cid"])

            # Create a variable using the template definition
            var = Variable(
                name="from-var-template",
                definition=definition,
                enabled=True
            )
            db.session.add(var)
            db.session.commit()

            # Verify the variable works
            created_var = Variable.query.filter_by(name="from-var-template").first()
            assert created_var is not None
            assert created_var.definition == "working-variable-content"

    # --- Tests for Adding Upload Templates to templates.source.json ---

    def test_added_upload_template_is_in_boot_image(self):
        """Test that an upload template added to templates.source.json is in the boot image."""
        # Add an upload template
        self._add_upload_template_to_templates_source(
            "custom-upload-template",
            "Custom Upload Template",
            "A custom upload template for testing",
            "<html><body>Custom upload content</body></html>"
        )

        # Generate boot image
        generator = BootImageGenerator(self.project_dir)
        generator.generate()

        # Read generated templates.json
        templates_json_path = self.project_dir / "reference_templates" / "templates.json"
        templates_data = json.loads(templates_json_path.read_text())

        # Verify the upload template is in templates.json
        assert "custom-upload-template" in templates_data["uploads"]
        assert templates_data["uploads"]["custom-upload-template"]["name"] == "Custom Upload Template"

    def test_boot_cid_shows_upload_template_in_variables_templates(self):
        """Test that booting with CID includes the upload template in /variables/templates."""
        # Add an upload template
        self._add_upload_template_to_templates_source(
            "accessible-upload-template",
            "Accessible Upload",
            "An accessible upload template",
            "<html><body>Accessible content</body></html>"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is accessible
        with self.app.app_context():
            templates_config = get_templates_config()
            assert templates_config is not None
            assert "accessible-upload-template" in templates_config["uploads"]

    def test_loaded_upload_template_can_be_used(self):
        """Test that the user can use the upload template to upload new files."""
        # Add an upload template
        self._add_upload_template_to_templates_source(
            "usable-upload-template",
            "Usable Upload Template",
            "A usable upload template",
            "<html><body>Usable upload content</body></html>"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify template is usable
        with self.app.app_context():
            template = get_template_by_key("uploads", "usable-upload-template")
            assert template is not None
            assert template["name"] == "Usable Upload Template"
            assert "content_cid" in template

    def test_upload_from_template_contains_expected_content(self):
        """Test that the upload from the template contains the expected content."""
        expected_content = "<html><body>Working upload content</body></html>"

        # Add an upload template with specific content
        self._add_upload_template_to_templates_source(
            "working-upload-template",
            "Working Upload",
            "A working upload template",
            expected_content
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Get template content
        with self.app.app_context():
            template = get_template_by_key("uploads", "working-upload-template")
            content_cid = template["content_cid"]

            # Resolve the content
            content = resolve_cid_value(content_cid)
            assert content is not None
            assert expected_content in content

    # --- Combined Test - All Types Together ---

    def test_complete_workflow_with_all_types(self):
        """Test a complete workflow adding all types of content at once."""
        # Add alias to boot
        self._add_alias_to_boot_source(
            "complete-alias",
            "literal /complete -> /complete-target"
        )

        # Add server to boot
        self._add_server_to_boot_source(
            "complete-server",
            "def main(context):\n    return 'Complete'\n"
        )

        # Add variable to boot
        self._add_variable_to_boot_source("complete-var", "complete-value")

        # Add alias template
        self._add_alias_template_to_templates_source(
            "complete-alias-template",
            "Complete Alias Template",
            "Complete alias template",
            "literal /template -> /template-target"
        )

        # Add server template
        self._add_server_template_to_templates_source(
            "complete-server-template",
            "Complete Server Template",
            "Complete server template",
            "def main(context):\n    return 'Template server'\n"
        )

        # Add variable template
        self._add_variable_template_to_templates_source(
            "complete-var-template",
            "Complete Variable Template",
            "Complete variable template",
            "template-variable-value"
        )

        # Add upload template
        self._add_upload_template_to_templates_source(
            "complete-upload-template",
            "Complete Upload Template",
            "Complete upload template",
            "<html>Complete</html>"
        )

        # Generate and import
        self._generate_and_import_boot_image()

        # Verify all content
        with self.app.app_context():
            # Boot content
            alias = Alias.query.filter_by(name='complete-alias').first()
            assert alias is not None

            server = Server.query.filter_by(name='complete-server').first()
            assert server is not None

            var = Variable.query.filter_by(name='complete-var').first()
            assert var is not None

            # Templates
            templates_config = get_templates_config()
            assert templates_config is not None

            assert "complete-alias-template" in templates_config["aliases"]
            assert "complete-server-template" in templates_config["servers"]
            assert "complete-var-template" in templates_config["variables"]
            assert "complete-upload-template" in templates_config["uploads"]
