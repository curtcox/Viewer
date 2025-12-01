"""Integration tests for boot image generated from reference_templates."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

import main
from app import create_app, db
from db_access import create_cid_record
from db_access.cids import get_cid_by_path
from generate_boot_image import BootImageGenerator
from models import Alias, Server, Variable
from template_manager import get_templates_config

pytestmark = pytest.mark.integration


class TestBootImageReferenceTemplates:
    """Integration tests for reference_templates boot image."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment."""
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

        yield

        # Restore original app
        main.app = original_app

        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def load_cids_into_db(self, generator: BootImageGenerator):
        """Load all CIDs from the generator's cids directory into the database.

        Args:
            generator: The BootImageGenerator instance
        """
        with self.app.app_context():
            cids_dir = generator.cids_dir
            for cid_file in cids_dir.iterdir():
                if cid_file.is_file():
                    cid = cid_file.name
                    cid_path = f"/{cid}"

                    # Skip if CID already exists in database
                    if get_cid_by_path(cid_path):
                        continue

                    content = cid_file.read_bytes()
                    create_cid_record(cid, content)

    def test_boot_image_loads_aliases(self, tmp_path):
        """Test that aliases from boot.source.json are loaded."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify output
        output = captured_output.getvalue()
        assert f"Boot CID {boot_cid} imported successfully" in output

        # Verify the alias was imported
        with self.app.app_context():
            alias = Alias.query.filter_by(name='ai').first()
            assert alias is not None, "Alias 'ai' should be loaded from boot image"
            assert 'ai -> /ai_stub' in alias.definition
            assert alias.enabled is True

    def test_boot_image_loads_servers(self, tmp_path):
        """Test that servers from boot.source.json are loaded."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify the server was imported
        with self.app.app_context():
            server = Server.query.filter_by(name='ai_stub').first()
            assert server is not None, "Server 'ai_stub' should be loaded from boot image"
            assert 'def main(' in server.definition
            assert server.enabled is True

    def test_boot_image_loads_templates_variable(self, tmp_path):
        """Test that templates variable from boot.source.json is loaded with correct CID."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']
        templates_cid = result['templates_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify the templates variable was imported
        with self.app.app_context():
            templates_var = Variable.query.filter_by(
                name='templates'
            ).first()
            assert templates_var is not None, "Variable 'templates' should be loaded from boot image"
            assert templates_var.definition == templates_cid
            assert templates_var.enabled is True

    def test_boot_image_templates_are_accessible(self, tmp_path):
        """Test that templates defined in templates.source.json are accessible."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify templates are accessible
        with self.app.app_context():
            templates_config = get_templates_config()
            assert templates_config is not None, "Templates config should be loaded"

            # Verify templates.source.json templates are present
            assert 'aliases' in templates_config
            assert 'servers' in templates_config
            assert 'variables' in templates_config
            assert 'uploads' in templates_config

            # Check specific templates from templates.source.json
            assert 'ai-shortcut' in templates_config['aliases']
            assert templates_config['aliases']['ai-shortcut']['name'] == 'AI Alias'

            assert 'echo' in templates_config['servers']
            assert templates_config['servers']['echo']['name'] == 'Echo request context'

            assert 'example-variable' in templates_config['variables']
            assert templates_config['variables']['example-variable']['name'] == 'Example Variable'

            assert 'hello-world' in templates_config['uploads']
            assert templates_config['uploads']['hello-world']['name'] == 'Hello World HTML page'
            assert 'embedded-cid-execution' in templates_config['uploads']
            assert (
                templates_config['uploads']['embedded-cid-execution']['name']
                == 'Embedded CID execution guide'
            )

    def test_boot_image_template_definitions_resolve(self, tmp_path):
        """Test that template definitions are properly resolved from CIDs."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify template definitions resolve correctly
        with self.app.app_context():
            templates_config = get_templates_config()

            # Get the AI alias template
            ai_alias_template = templates_config['aliases']['ai-shortcut']
            assert 'definition_cid' in ai_alias_template
            # The CID should be valid and stored
            definition_cid = ai_alias_template['definition_cid']
            assert len(definition_cid) >= 8

            # Get the echo server template
            echo_server_template = templates_config['servers']['echo']
            assert 'definition_cid' in echo_server_template
            server_definition_cid = echo_server_template['definition_cid']
            assert len(server_definition_cid) >= 8

    def test_boot_image_complete_workflow(self, tmp_path):
        """Test the complete boot image workflow end-to-end."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        boot_cid = result['boot_cid']
        templates_cid = result['templates_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()
        assert f"Boot CID {boot_cid} imported successfully" in output

        # Verify complete workflow
        with self.app.app_context():
            # 1. Alias is loaded
            alias = Alias.query.filter_by(name='ai').first()
            assert alias is not None
            assert alias.enabled is True

            # 2. Server is loaded
            server = Server.query.filter_by(name='ai_stub').first()
            assert server is not None
            assert server.enabled is True

            # 3. Templates variable is loaded with correct CID
            templates_var = Variable.query.filter_by(
                name='templates'
            ).first()
            assert templates_var is not None
            assert templates_var.definition == templates_cid
            assert templates_var.enabled is True

            # 4. Templates are accessible and complete
            templates_config = get_templates_config()
            assert templates_config is not None

            # Verify all template categories exist
            assert len(templates_config['aliases']) > 0
            assert len(templates_config['servers']) > 0
            assert len(templates_config['variables']) > 0
            assert len(templates_config['uploads']) > 0

            # Verify specific templates
            assert 'ai-shortcut' in templates_config['aliases']
            assert 'echo' in templates_config['servers']
            assert 'example-variable' in templates_config['variables']
            assert 'hello-world' in templates_config['uploads']

    def test_minimal_boot_cid_loads_only_ai_stub(self, tmp_path):
        """Test that minimal boot CID loads only the ai_stub server."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        minimal_boot_cid = result['minimal_boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(minimal_boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify only the ai_stub server was imported
        with self.app.app_context():
            servers = Server.query.all()
            server_names = [s.name for s in servers]
            assert 'ai_stub' in server_names, "ai_stub should be loaded from minimal boot"
            # Verify extra default servers are NOT loaded
            assert 'echo' not in server_names, "echo should NOT be loaded from minimal boot"
            assert 'shell' not in server_names, "shell should NOT be loaded from minimal boot"
            assert 'glom' not in server_names, "glom should NOT be loaded from minimal boot"

    def test_default_boot_cid_loads_all_servers(self, tmp_path):
        """Test that default boot CID loads all servers."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        default_boot_cid = result['default_boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(default_boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify all servers were imported
        with self.app.app_context():
            servers = Server.query.all()
            server_names = [s.name for s in servers]
            # Verify all default servers are loaded
            assert 'ai_stub' in server_names, "ai_stub should be loaded from default boot"
            assert 'echo' in server_names, "echo should be loaded from default boot"
            assert 'shell' in server_names, "shell should be loaded from default boot"
            assert 'glom' in server_names, "glom should be loaded from default boot"
            assert 'markdown' in server_names, "markdown should be loaded from default boot"
            assert 'jinja' in server_names, "jinja should be loaded from default boot"
            assert 'proxy' in server_names, "proxy should be loaded from default boot"
            assert 'pygments' in server_names, "pygments should be loaded from default boot"

    def test_default_boot_cid_echo_server_works(self, tmp_path):
        """Test that echo server works when booted from default CID."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        default_boot_cid = result['default_boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(default_boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify echo server is available and works
        with self.app.app_context():
            server = Server.query.filter_by(name='echo').first()
            assert server is not None, "echo server should be loaded from default boot"
            assert server.enabled is True
            # Verify the definition contains expected content
            assert 'def main(' in server.definition or 'dict_to_html_ul' in server.definition

    def test_default_boot_cid_shell_server_works(self, tmp_path):
        """Test that shell server works when booted from default CID."""
        # Generate boot image
        project_dir = Path(__file__).parent.parent.parent
        generator = BootImageGenerator(project_dir)
        result = generator.generate()
        default_boot_cid = result['default_boot_cid']

        # Load all CIDs into database
        self.load_cids_into_db(generator)

        # Import boot CID
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(default_boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify shell server is available and works
        with self.app.app_context():
            server = Server.query.filter_by(name='shell').first()
            assert server is not None, "shell server should be loaded from default boot"
            assert server.enabled is True
            # Verify the definition contains expected content
            assert 'def main(' in server.definition
            assert 'subprocess' in server.definition or 'shell' in server.definition.lower()
