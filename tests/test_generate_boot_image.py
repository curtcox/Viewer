"""Unit tests for generate_boot_image.py."""

import json

import pytest

from cid_core import generate_cid
from generate_boot_image import BootImageGenerator


class TestBootImageGenerator:
    """Test the BootImageGenerator class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure for testing."""
        # Create directories
        ref_templates = tmp_path / "reference_templates"
        ref_templates.mkdir()
        (ref_templates / "aliases").mkdir()
        (ref_templates / "variables").mkdir()
        (ref_templates / "servers").mkdir()
        (ref_templates / "servers" / "definitions").mkdir()
        (ref_templates / "uploads").mkdir()
        (ref_templates / "uploads" / "contents").mkdir()
        (tmp_path / "cids").mkdir()

        # Create test files
        alias_file = ref_templates / "aliases" / "test.txt"
        alias_file.write_text("literal /test -> /target")

        var_file = ref_templates / "variables" / "test_var.txt"
        var_file.write_text("test value")

        server_file = ref_templates / "servers" / "definitions" / "test_server.py"
        server_file.write_text("def main():\n    return 'Hello'\n")

        upload_file = ref_templates / "uploads" / "contents" / "test.html"
        upload_file.write_text("<html><body>Test</body></html>")

        # Create templates.source.json
        templates_source = {
            "aliases": {
                "test-alias": {
                    "name": "Test Alias",
                    "description": "Test alias description",
                    "definition_cid": "reference_templates/aliases/test.txt"
                }
            },
            "servers": {
                "test-server": {
                    "name": "Test Server",
                    "description": "Test server description",
                    "definition_cid": "reference_templates/servers/definitions/test_server.py"
                }
            },
            "variables": {
                "test-variable": {
                    "name": "Test Variable",
                    "description": "Test variable description",
                    "definition_cid": "reference_templates/variables/test_var.txt"
                }
            },
            "secrets": {},
            "uploads": {
                "test-upload": {
                    "name": "Test Upload",
                    "description": "Test upload description",
                    "content_cid": "reference_templates/uploads/contents/test.html"
                }
            }
        }
        templates_source_file = ref_templates / "templates.source.json"
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        # Create boot.source.json
        boot_source = {
            "version": 6,
            "runtime": '{"python": {"version": "3.11.0", "implementation": "CPython"}}',
            "project_files": "{}",
            "aliases": [
                {
                    "name": "test",
                    "definition_cid": "reference_templates/aliases/test.txt",
                    "enabled": True
                }
            ],
            "servers": [
                {
                    "name": "test_server",
                    "definition_cid": "reference_templates/servers/definitions/test_server.py",
                    "enabled": True
                }
            ],
            "variables": [
                {
                    "name": "templates",
                    "definition": "GENERATED:templates.json",
                    "enabled": True
                }
            ]
        }
        boot_source_file = ref_templates / "boot.source.json"
        boot_source_file.write_text(json.dumps(boot_source, indent=2))

        # Create minimal.boot.source.json (same as boot.source.json)
        minimal_boot_source_file = ref_templates / "minimal.boot.source.json"
        minimal_boot_source_file.write_text(json.dumps(boot_source, indent=2))

        # Create default.boot.source.json (with all servers for default)
        default_boot_source = boot_source.copy()
        default_boot_source_file = ref_templates / "default.boot.source.json"
        default_boot_source_file.write_text(json.dumps(default_boot_source, indent=2))

        return tmp_path

    def test_init(self, temp_project):
        """Test BootImageGenerator initialization."""
        generator = BootImageGenerator(temp_project)
        assert generator.base_dir == temp_project
        assert generator.reference_templates_dir == temp_project / "reference_templates"
        assert generator.cids_dir == temp_project / "cids"
        assert generator.processed_files == set()
        assert not generator.file_to_cid

    def test_ensure_cids_directory(self, temp_project):
        """Test that cids directory is created if it doesn't exist."""
        cids_dir = temp_project / "cids"
        cids_dir.rmdir()  # Remove it

        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        assert cids_dir.exists()
        assert cids_dir.is_dir()

    def test_read_file_content(self, temp_project):
        """Test reading file content."""
        generator = BootImageGenerator(temp_project)
        test_file = temp_project / "test.txt"
        test_file.write_bytes(b"test content")

        content = generator.read_file_content(test_file)
        assert content == b"test content"

    def test_generate_and_store_cid(self, temp_project):
        """Test generating and storing a CID."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        test_file = temp_project / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        cid = generator.generate_and_store_cid(test_file, "test.txt")

        # Verify CID is correct
        expected_cid = generate_cid(test_content)
        assert cid == expected_cid

        # Verify CID file was created
        cid_file = temp_project / "cids" / cid
        assert cid_file.exists()
        assert cid_file.read_bytes() == test_content

        # Verify tracking
        assert "test.txt" in generator.file_to_cid
        assert generator.file_to_cid["test.txt"] == cid
        assert "test.txt" in generator.processed_files

    def test_generate_and_store_cid_idempotent(self, temp_project):
        """Test that generating the same CID twice is idempotent."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        test_file = temp_project / "test.txt"
        test_file.write_bytes(b"test content")

        cid1 = generator.generate_and_store_cid(test_file, "test.txt")
        cid2 = generator.generate_and_store_cid(test_file, "test.txt")

        assert cid1 == cid2

    def test_process_referenced_files(self, temp_project):
        """Test processing referenced files in JSON data."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        # Create a test file
        test_file = temp_project / "reference_templates" / "test.txt"
        test_file.write_text("content")

        data = {
            "aliases": {
                "test": {
                    "name": "Test",
                    "definition_cid": "reference_templates/test.txt"
                }
            }
        }

        generator.process_referenced_files(data)

        # Verify the file was processed
        assert "reference_templates/test.txt" in generator.processed_files
        assert "reference_templates/test.txt" in generator.file_to_cid

    def test_replace_filenames_with_cids(self, temp_project):
        """Test replacing filenames with CIDs."""
        generator = BootImageGenerator(temp_project)

        # Mock the file_to_cid mapping
        generator.file_to_cid = {
            "reference_templates/test.txt": "TESTCID123"
        }

        data = {
            "aliases": {
                "test": {
                    "name": "Test",
                    "definition_cid": "reference_templates/test.txt"
                }
            }
        }

        result = generator.replace_filenames_with_cids(data)

        assert result["aliases"]["test"]["definition_cid"] == "TESTCID123"
        assert result["aliases"]["test"]["name"] == "Test"

    def test_generate_templates_json(self, temp_project):
        """Test generating templates.json."""
        generator = BootImageGenerator(temp_project)

        templates_cid = generator.generate_templates_json()

        # Verify templates.json was created
        templates_json_path = temp_project / "reference_templates" / "templates.json"
        assert templates_json_path.exists()

        # Verify templates.json has correct structure
        with open(templates_json_path, 'r', encoding='utf-8') as f:
            templates_data = json.load(f)

        assert "aliases" in templates_data
        assert "servers" in templates_data
        assert "variables" in templates_data
        assert "secrets" in templates_data
        assert "uploads" in templates_data

        # Verify CIDs were replaced
        assert templates_data["aliases"]["test-alias"]["definition_cid"].startswith("AAAAAAA")

        # Verify CID file was created
        cid_file = temp_project / "cids" / templates_cid
        assert cid_file.exists()

    def test_generate_boot_json(self, temp_project):
        """Test generating boot.json."""
        generator = BootImageGenerator(temp_project)

        # First generate templates.json
        templates_cid = generator.generate_templates_json()

        # Then generate boot.json
        boot_cid = generator.generate_boot_json(templates_cid)

        # Verify boot.json was created
        boot_json_path = temp_project / "reference_templates" / "boot.json"
        assert boot_json_path.exists()

        # Verify boot.json has correct structure
        with open(boot_json_path, 'r', encoding='utf-8') as f:
            boot_data = json.load(f)

        assert "version" in boot_data
        assert boot_data["version"] == 6
        assert "aliases" in boot_data
        assert "servers" in boot_data
        assert "variables" in boot_data

        # Verify CIDs were replaced
        assert boot_data["aliases"][0]["definition_cid"].startswith("AAAAAAA")
        assert boot_data["servers"][0]["definition_cid"].startswith("AAAAAAA")

        # Verify templates variable was set to templates CID
        templates_var = None
        for var in boot_data["variables"]:
            if var["name"] == "templates":
                templates_var = var
                break

        assert templates_var is not None
        assert templates_var["definition"] == templates_cid
        assert templates_var["definition"] != "GENERATED:templates.json"

        # Verify CID file was created
        cid_file = temp_project / "cids" / boot_cid
        assert cid_file.exists()

    def test_generate_complete(self, temp_project):
        """Test the complete generation process."""
        generator = BootImageGenerator(temp_project)

        result = generator.generate()

        # Verify result has the expected keys
        assert "templates_cid" in result
        assert "boot_cid" in result
        assert "minimal_boot_cid" in result
        assert "default_boot_cid" in result

        # Verify both CIDs are valid (at least 8 characters, valid CID format)
        assert len(result["templates_cid"]) >= 8
        assert len(result["boot_cid"]) >= 8
        assert len(result["minimal_boot_cid"]) >= 8
        assert len(result["default_boot_cid"]) >= 8
        # All CIDs should be alphanumeric with _ and - allowed
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', result["templates_cid"])
        assert re.match(r'^[A-Za-z0-9_-]+$', result["boot_cid"])
        assert re.match(r'^[A-Za-z0-9_-]+$', result["minimal_boot_cid"])
        assert re.match(r'^[A-Za-z0-9_-]+$', result["default_boot_cid"])

        # Verify files were created
        assert (temp_project / "reference_templates" / "templates.json").exists()
        assert (temp_project / "reference_templates" / "boot.json").exists()
        assert (temp_project / "reference_templates" / "minimal.boot.json").exists()
        assert (temp_project / "reference_templates" / "default.boot.json").exists()

        # Verify CID files were created
        assert (temp_project / "cids" / result["templates_cid"]).exists()
        assert (temp_project / "cids" / result["boot_cid"]).exists()
        assert (temp_project / "cids" / result["minimal_boot_cid"]).exists()
        assert (temp_project / "cids" / result["default_boot_cid"]).exists()

        # Verify processed files
        assert len(generator.processed_files) > 0

    def test_generate_with_missing_file(self, temp_project):
        """Test that generation handles missing files gracefully."""
        generator = BootImageGenerator(temp_project)

        # Add a reference to a non-existent file in templates.source.json
        templates_source_file = temp_project / "reference_templates" / "templates.source.json"
        with open(templates_source_file, 'r', encoding='utf-8') as f:
            templates_data = json.load(f)

        templates_data["servers"]["missing"] = {
            "name": "Missing Server",
            "definition_cid": "reference_templates/servers/definitions/missing.py"
        }

        with open(templates_source_file, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, indent=2)

        # Should complete without error (with warning)
        result = generator.generate()

        assert "templates_cid" in result
        assert "boot_cid" in result

    def test_replace_filenames_preserves_other_fields(self, temp_project):
        """Test that replacing filenames preserves other fields."""
        generator = BootImageGenerator(temp_project)

        generator.file_to_cid = {
            "reference_templates/test.txt": "TESTCID123"
        }

        data = {
            "aliases": {
                "test": {
                    "name": "Test Name",
                    "description": "Test Description",
                    "definition_cid": "reference_templates/test.txt",
                    "metadata": {"key": "value"}
                }
            }
        }

        result = generator.replace_filenames_with_cids(data)

        assert result["aliases"]["test"]["name"] == "Test Name"
        assert result["aliases"]["test"]["description"] == "Test Description"
        assert result["aliases"]["test"]["definition_cid"] == "TESTCID123"
        assert result["aliases"]["test"]["metadata"] == {"key": "value"}

    def test_process_referenced_files_with_arrays(self, temp_project):
        """Test processing referenced files in arrays."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        # Create test files
        test_file1 = temp_project / "reference_templates" / "test1.txt"
        test_file1.write_text("content1")
        test_file2 = temp_project / "reference_templates" / "test2.txt"
        test_file2.write_text("content2")

        data = [
            {
                "name": "test1",
                "definition_cid": "reference_templates/test1.txt"
            },
            {
                "name": "test2",
                "definition_cid": "reference_templates/test2.txt"
            }
        ]

        generator.process_referenced_files(data)

        assert "reference_templates/test1.txt" in generator.processed_files
        assert "reference_templates/test2.txt" in generator.processed_files
