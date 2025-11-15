"""Integration tests for boot CID command-line interface."""

from __future__ import annotations

import json
import sys
from io import StringIO

import pytest

import main
from app import create_app, db
from cid_utils import generate_cid
from db_access import create_cid_record
from models import Alias, Server

pytestmark = pytest.mark.integration


class TestBootCidCLI:
    """Integration tests for boot CID CLI functionality."""

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

    def test_handle_boot_cid_import_success(self):
        """Test successful boot CID import via CLI handler."""
        with self.app.app_context():
            # Create alias content
            aliases_data = [
                {
                    'name': 'cli-test-alias',
                    'definition': '/cli-test -> /cli-target',
                }
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            # Create boot CID
            payload_data = {
                'version': 6,
                'aliases': aliases_cid,
            }
            content = json.dumps(payload_data).encode('utf-8')
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

        # Capture stdout
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            # Call the CLI handler (should not raise)
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify the output contains success message
        output = captured_output.getvalue()
        assert f"Boot CID {boot_cid} imported successfully" in output

        # Verify the alias was imported
        with self.app.app_context():
            alias = Alias.query.filter_by(name='cli-test-alias').first()
            assert alias is not None
            assert alias.definition == '/cli-test -> /cli-target'

    def test_handle_boot_cid_import_missing_dependency_exits(self):
        """Test that missing dependency causes SystemExit with helpful message."""
        with self.app.app_context():
            # Create boot CID that references a non-existent CID
            missing_cid = generate_cid(b"missing content")
            payload_data = {
                'version': 6,
                'aliases': missing_cid,
            }
            content = json.dumps(payload_data).encode('utf-8')
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

        # Capture stderr
        captured_error = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_error

        try:
            # Should exit with status 1
            with pytest.raises(SystemExit) as exc_info:
                main.handle_boot_cid_import(boot_cid)

            # Verify exit code
            assert exc_info.value.code == 1

            # Verify error message
            error_output = captured_error.getvalue()
            assert "Boot CID import failed" in error_output
            assert "missing from the database" in error_output
            assert f"/{missing_cid}" in error_output
        finally:
            sys.stderr = old_stderr

    def test_handle_boot_cid_import_invalid_cid_exits(self):
        """Test that invalid CID format causes SystemExit with helpful message."""
        # Capture stderr
        captured_error = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_error

        try:
            # Should exit with status 1
            with pytest.raises(SystemExit) as exc_info:
                main.handle_boot_cid_import("not-a-valid-cid")

            # Verify exit code
            assert exc_info.value.code == 1

            # Verify error message
            error_output = captured_error.getvalue()
            assert "Boot CID import failed" in error_output
            assert "Invalid CID format" in error_output
        finally:
            sys.stderr = old_stderr

    def test_handle_boot_cid_import_with_multiple_entities(self):
        """Test boot CID import with multiple entity types."""
        with self.app.app_context():
            # Create alias content
            aliases_data = [
                {
                    'name': 'multi-alias',
                    'definition': '/multi -> /target',
                }
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)
            create_cid_record(aliases_cid, aliases_content)

            # Create server content
            servers_data = [
                {
                    'name': 'multi-server',
                    'definition': 'echo "multi"',
                }
            ]
            servers_content = json.dumps(servers_data).encode('utf-8')
            servers_cid = generate_cid(servers_content)
            create_cid_record(servers_cid, servers_content)

            # Create boot CID with both
            payload_data = {
                'version': 6,
                'aliases': aliases_cid,
                'servers': servers_cid,
            }
            content = json.dumps(payload_data).encode('utf-8')
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

        # Capture stdout
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify both entities were imported
        with self.app.app_context():
            alias = Alias.query.filter_by(name='multi-alias').first()
            assert alias is not None

            server = Server.query.filter_by(name='multi-server').first()
            assert server is not None

    def test_handle_boot_cid_import_with_cid_values(self):
        """Test boot CID import with embedded cid_values section."""
        with self.app.app_context():
            # Create alias content (will be in cid_values, not separate CID in DB)
            aliases_data = [
                {
                    'name': 'embedded-alias',
                    'definition': '/embedded -> /target',
                }
            ]
            aliases_content = json.dumps(aliases_data).encode('utf-8')
            aliases_cid = generate_cid(aliases_content)

            # Create boot CID with cid_values section
            payload_data = {
                'version': 6,
                'aliases': aliases_cid,
                'cid_values': {
                    aliases_cid: aliases_content.decode('utf-8'),
                },
            }
            content = json.dumps(payload_data).encode('utf-8')
            boot_cid = generate_cid(content)
            create_cid_record(boot_cid, content)

        # Capture stdout
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            main.handle_boot_cid_import(boot_cid)
        finally:
            sys.stdout = old_stdout

        # Verify the alias was imported even though its CID wasn't in DB
        with self.app.app_context():
            alias = Alias.query.filter_by(name='embedded-alias').first()
            assert alias is not None
