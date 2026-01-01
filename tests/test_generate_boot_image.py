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
        (ref_templates / "gateways").mkdir()
        (ref_templates / "gateways" / "transforms").mkdir()
        (ref_templates / "gateways" / "templates").mkdir()
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

        # Create gateways.source.json and referenced transform files
        (ref_templates / "gateways" / "transforms" / "test_request.py").write_text(
            "def transform_request(request_details, context):\n    return request_details\n"
        )
        (ref_templates / "gateways" / "transforms" / "test_response.py").write_text(
            "def transform_response(response_details, context):\n    return response_details\n"
        )
        gateways_source = {
            "test-gateway": {
                "target_url": "https://test.example.com",
                "request_transform_cid": "reference_templates/gateways/transforms/test_request.py",
                "response_transform_cid": "reference_templates/gateways/transforms/test_response.py",
                "description": "Test gateway",
            },
            "another-gateway": {
                "target_url": "https://another.example.com",
                "request_transform_cid": "reference_templates/gateways/transforms/test_request.py",
                "response_transform_cid": "reference_templates/gateways/transforms/test_response.py",
                "description": "Another gateway",
            },
        }
        (ref_templates / "gateways.source.json").write_text(
            json.dumps(gateways_source, indent=2)
        )

        # Create templates.source.json
        templates_source = {
            "aliases": {
                "test-alias": {
                    "name": "Test Alias",
                    "description": "Test alias description",
                    "definition_cid": "reference_templates/aliases/test.txt",
                }
            },
            "servers": {
                "test-server": {
                    "name": "Test Server",
                    "description": "Test server description",
                    "definition_cid": "reference_templates/servers/definitions/test_server.py",
                }
            },
            "variables": {
                "test-variable": {
                    "name": "Test Variable",
                    "description": "Test variable description",
                    "definition_cid": "reference_templates/variables/test_var.txt",
                }
            },
            "secrets": {},
            "uploads": {
                "test-upload": {
                    "name": "Test Upload",
                    "description": "Test upload description",
                    "content_cid": "reference_templates/uploads/contents/test.html",
                }
            },
        }
        templates_source_file = ref_templates / "templates.source.json"
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        # Create uis.source.json
        uis_source = {"aliases": {}, "servers": {}, "variables": {}}
        uis_source_file = ref_templates / "uis.source.json"
        uis_source_file.write_text(json.dumps(uis_source, indent=2))

        # Create boot.source.json
        boot_source = {
            "version": 6,
            "runtime": '{"python": {"version": "3.11.0", "implementation": "CPython"}}',
            "project_files": "{}",
            "aliases": [
                {
                    "name": "test",
                    "definition_cid": "reference_templates/aliases/test.txt",
                    "enabled": True,
                }
            ],
            "servers": [
                {
                    "name": "test_server",
                    "definition_cid": "reference_templates/servers/definitions/test_server.py",
                    "enabled": True,
                }
            ],
            "variables": [
                {
                    "name": "templates",
                    "definition": "GENERATED:templates.json",
                    "enabled": True,
                },
                {"name": "uis", "definition": "GENERATED:uis.json", "enabled": True},
                {
                    "name": "gateways",
                    "definition": "GENERATED:gateways.json",
                    "enabled": True,
                },
            ],
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

        # Create readonly.boot.source.json (same as boot but for readonly mode)
        readonly_boot_source = boot_source.copy()
        readonly_boot_source_file = ref_templates / "readonly.boot.source.json"
        readonly_boot_source_file.write_text(json.dumps(readonly_boot_source, indent=2))

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
        """Test generating and storing a CID for content > 64 bytes (hashed CID)."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        test_file = temp_project / "test.txt"
        # Use content > 64 bytes to ensure it generates a hashed CID (94 chars)
        test_content = b"This is a longer test content that exceeds 64 bytes to ensure a hashed CID is generated instead of a literal one"
        test_file.write_bytes(test_content)

        cid = generator.generate_and_store_cid(test_file, "test.txt")

        # Verify CID is correct
        expected_cid = generate_cid(test_content)
        assert cid == expected_cid

        # Verify it's a hashed CID (exactly 94 characters)
        assert len(cid) == 94

        # Verify CID file was created (only hashed CIDs are stored)
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
        # Use content > 64 bytes to generate a hashed CID
        test_file.write_bytes(
            b"This is a longer test content that exceeds 64 bytes to ensure a hashed CID is generated"
        )

        cid1 = generator.generate_and_store_cid(test_file, "test.txt")
        cid2 = generator.generate_and_store_cid(test_file, "test.txt")

        assert cid1 == cid2

    def test_generate_and_store_cid_literal(self, temp_project):
        """Test that literal CIDs (< 94 chars) are NOT stored in /cids."""
        generator = BootImageGenerator(temp_project)
        generator.ensure_cids_directory()

        test_file = temp_project / "test.txt"
        # Use content <= 64 bytes to generate a literal CID
        test_content = b"short content"
        test_file.write_bytes(test_content)

        cid = generator.generate_and_store_cid(test_file, "test.txt")

        # Verify CID is correct
        expected_cid = generate_cid(test_content)
        assert cid == expected_cid

        # Verify it's a literal CID (< 94 characters)
        assert len(cid) < 94

        # Verify CID file was NOT created (literal CIDs are not stored)
        cid_file = temp_project / "cids" / cid
        assert not cid_file.exists()

        # Verify tracking still works
        assert "test.txt" in generator.file_to_cid
        assert generator.file_to_cid["test.txt"] == cid
        assert "test.txt" in generator.processed_files

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
                    "definition_cid": "reference_templates/test.txt",
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
        generator.file_to_cid = {"reference_templates/test.txt": "TESTCID123"}

        data = {
            "aliases": {
                "test": {
                    "name": "Test",
                    "definition_cid": "reference_templates/test.txt",
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
        with open(templates_json_path, "r", encoding="utf-8") as f:
            templates_data = json.load(f)

        assert "aliases" in templates_data
        assert "servers" in templates_data
        assert "variables" in templates_data
        assert "secrets" in templates_data
        assert "uploads" in templates_data

        # Verify CIDs were replaced
        assert templates_data["aliases"]["test-alias"]["definition_cid"].startswith(
            "AAAAAAA"
        )

        # Verify CID file was created only if it's a hashed CID (>= 94 chars)
        cid_file = temp_project / "cids" / templates_cid
        if len(templates_cid) >= 94:
            assert cid_file.exists()
        else:
            # Literal CIDs are not stored in /cids
            assert not cid_file.exists()

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
        with open(boot_json_path, "r", encoding="utf-8") as f:
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

        # Verify CID file was created only if it's a hashed CID (>= 94 chars)
        cid_file = temp_project / "cids" / boot_cid
        if len(boot_cid) >= 94:
            assert cid_file.exists()
        else:
            # Literal CIDs are not stored in /cids
            assert not cid_file.exists()

    def test_generate_complete(self, temp_project):
        """Test the complete generation process."""
        generator = BootImageGenerator(temp_project)

        result = generator.generate()

        # Verify result has the expected keys
        assert "templates_cid" in result
        assert "boot_cid" in result
        assert "minimal_boot_cid" in result
        assert "default_boot_cid" in result
        assert "readonly_boot_cid" in result

        # Verify both CIDs are valid (at least 8 characters, valid CID format)
        assert len(result["templates_cid"]) >= 8
        assert len(result["boot_cid"]) >= 8
        assert len(result["minimal_boot_cid"]) >= 8
        assert len(result["default_boot_cid"]) >= 8
        assert len(result["readonly_boot_cid"]) >= 8
        # All CIDs should be alphanumeric with _ and - allowed
        import re

        assert re.match(r"^[A-Za-z0-9_-]+$", result["templates_cid"])
        assert re.match(r"^[A-Za-z0-9_-]+$", result["boot_cid"])
        assert re.match(r"^[A-Za-z0-9_-]+$", result["minimal_boot_cid"])
        assert re.match(r"^[A-Za-z0-9_-]+$", result["default_boot_cid"])
        assert re.match(r"^[A-Za-z0-9_-]+$", result["readonly_boot_cid"])

        # Verify files were created
        assert (temp_project / "reference_templates" / "templates.json").exists()
        assert (temp_project / "reference_templates" / "boot.json").exists()
        assert (temp_project / "reference_templates" / "minimal.boot.json").exists()
        assert (temp_project / "reference_templates" / "default.boot.json").exists()
        assert (temp_project / "reference_templates" / "readonly.boot.json").exists()

        # Verify CID files were created only for hashed CIDs (>= 94 chars)
        # Literal CIDs (< 94 chars) are not stored in /cids
        if len(result["templates_cid"]) >= 94:
            assert (temp_project / "cids" / result["templates_cid"]).exists()
        if len(result["boot_cid"]) >= 94:
            assert (temp_project / "cids" / result["boot_cid"]).exists()
        if len(result["minimal_boot_cid"]) >= 94:
            assert (temp_project / "cids" / result["minimal_boot_cid"]).exists()
        if len(result["default_boot_cid"]) >= 94:
            assert (temp_project / "cids" / result["default_boot_cid"]).exists()
        if len(result["readonly_boot_cid"]) >= 94:
            assert (temp_project / "cids" / result["readonly_boot_cid"]).exists()

        # Verify processed files
        assert len(generator.processed_files) > 0

    def test_generate_with_missing_file(self, temp_project):
        """Test that generation handles missing files gracefully."""
        generator = BootImageGenerator(temp_project)

        # Add a reference to a non-existent file in templates.source.json
        templates_source_file = (
            temp_project / "reference_templates" / "templates.source.json"
        )
        with open(templates_source_file, "r", encoding="utf-8") as f:
            templates_data = json.load(f)

        templates_data["servers"]["missing"] = {
            "name": "Missing Server",
            "definition_cid": "reference_templates/servers/definitions/missing.py",
        }

        with open(templates_source_file, "w", encoding="utf-8") as f:
            json.dump(templates_data, f, indent=2)

        # Should complete without error (with warning)
        result = generator.generate()

        assert "templates_cid" in result
        assert "boot_cid" in result

    def test_replace_filenames_preserves_other_fields(self, temp_project):
        """Test that replacing filenames preserves other fields."""
        generator = BootImageGenerator(temp_project)

        generator.file_to_cid = {"reference_templates/test.txt": "TESTCID123"}

        data = {
            "aliases": {
                "test": {
                    "name": "Test Name",
                    "description": "Test Description",
                    "definition_cid": "reference_templates/test.txt",
                    "metadata": {"key": "value"},
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
            {"name": "test1", "definition_cid": "reference_templates/test1.txt"},
            {"name": "test2", "definition_cid": "reference_templates/test2.txt"},
        ]

        generator.process_referenced_files(data)

        assert "reference_templates/test1.txt" in generator.processed_files
        assert "reference_templates/test2.txt" in generator.processed_files


class TestGatewaysInBootImage:
    """Tests for gateways being properly added to boot images."""

    @pytest.fixture
    def temp_project_with_gateways(self, tmp_path):
        """Create a temporary project structure with gateways configuration."""
        # Create directories
        ref_templates = tmp_path / "reference_templates"
        ref_templates.mkdir()
        (ref_templates / "aliases").mkdir()
        (ref_templates / "variables").mkdir()
        (ref_templates / "servers").mkdir()
        (ref_templates / "servers" / "definitions").mkdir()
        (ref_templates / "gateways").mkdir()
        (ref_templates / "gateways" / "transforms").mkdir()
        (ref_templates / "gateways" / "templates").mkdir()
        (ref_templates / "uploads").mkdir()
        (ref_templates / "uploads" / "contents").mkdir()
        (tmp_path / "cids").mkdir()

        # Create test transform files for gateways
        request_transform = ref_templates / "gateways" / "transforms" / "test_request.py"
        request_transform.write_text(
            '''def transform_request(request_details: dict, context: dict) -> dict:
    return {"url": "https://test.example.com", "method": "GET"}
'''
        )

        response_transform = ref_templates / "gateways" / "transforms" / "test_response.py"
        response_transform.write_text(
            '''def transform_response(response_details: dict, context: dict) -> dict:
    return {"output": "test output", "content_type": "text/html"}
'''
        )

        # Create test template files
        page_template = ref_templates / "gateways" / "templates" / "test_page.html"
        page_template.write_text("<html><body>{{ content }}</body></html>")
        error_template = ref_templates / "gateways" / "templates" / "test_error.html"
        error_template.write_text("<html><body>Error: {{ message }}</body></html>")

        # Create test files
        alias_file = ref_templates / "aliases" / "test.txt"
        alias_file.write_text("literal /test -> /target")

        var_file = ref_templates / "variables" / "test_var.txt"
        var_file.write_text("test value")

        server_file = ref_templates / "servers" / "definitions" / "test_server.py"
        server_file.write_text("def main():\n    return 'Hello'\n")

        # Create templates.source.json
        templates_source = {
            "aliases": {},
            "servers": {},
            "variables": {},
            "secrets": {},
            "uploads": {},
        }
        templates_source_file = ref_templates / "templates.source.json"
        templates_source_file.write_text(json.dumps(templates_source, indent=2))

        # Create gateways.source.json with transform CIDs
        gateways_source = {
            "test-gateway": {
                "target_url": "https://test.example.com",
                "request_transform_cid": "reference_templates/gateways/transforms/test_request.py",
                "response_transform_cid": "reference_templates/gateways/transforms/test_response.py",
                "description": "Test gateway for unit testing",
                "templates": {
                    "test_page.html": "reference_templates/gateways/templates/test_page.html",
                    "test_error.html": "reference_templates/gateways/templates/test_error.html",
                },
            },
            "another-gateway": {
                "target_url": "https://another.example.com",
                "request_transform_cid": "reference_templates/gateways/transforms/test_request.py",
                "response_transform_cid": "reference_templates/gateways/transforms/test_response.py",
                "description": "Another test gateway",
            },
        }
        gateways_source_file = ref_templates / "gateways.source.json"
        gateways_source_file.write_text(json.dumps(gateways_source, indent=2))

        # Create uis.source.json
        uis_source = {"aliases": {}, "servers": {}, "variables": {}}
        uis_source_file = ref_templates / "uis.source.json"
        uis_source_file.write_text(json.dumps(uis_source, indent=2))

        # Create boot.source.json with gateways variable
        boot_source = {
            "version": 6,
            "runtime": '{"python": {"version": "3.11.0", "implementation": "CPython"}}',
            "project_files": "{}",
            "aliases": [],
            "servers": [],
            "variables": [
                {
                    "name": "templates",
                    "definition": "GENERATED:templates.json",
                    "enabled": True,
                },
                {"name": "uis", "definition": "GENERATED:uis.json", "enabled": True},
                {
                    "name": "gateways",
                    "definition": "GENERATED:gateways.json",
                    "enabled": True,
                },
            ],
        }
        boot_source_file = ref_templates / "boot.source.json"
        boot_source_file.write_text(json.dumps(boot_source, indent=2))

        # Create minimal.boot.source.json (same as boot.source.json)
        minimal_boot_source_file = ref_templates / "minimal.boot.source.json"
        minimal_boot_source_file.write_text(json.dumps(boot_source, indent=2))

        # Create default.boot.source.json (with gateways)
        default_boot_source_file = ref_templates / "default.boot.source.json"
        default_boot_source_file.write_text(json.dumps(boot_source, indent=2))

        # Create readonly.boot.source.json (with gateways)
        readonly_boot_source_file = ref_templates / "readonly.boot.source.json"
        readonly_boot_source_file.write_text(json.dumps(boot_source, indent=2))

        return tmp_path

    def test_generate_gateways_json_creates_file(self, temp_project_with_gateways):
        """Test that generate_gateways_json creates gateways.json file."""
        generator = BootImageGenerator(temp_project_with_gateways)
        generator.ensure_cids_directory()

        generator.generate_gateways_json()

        # Verify gateways.json was created
        gateways_json_path = temp_project_with_gateways / "reference_templates" / "gateways.json"
        assert gateways_json_path.exists(), "gateways.json should be created"

        # Verify it contains the gateway configurations
        with open(gateways_json_path, "r", encoding="utf-8") as f:
            gateways_data = json.load(f)

        assert "test-gateway" in gateways_data
        assert "another-gateway" in gateways_data
        assert gateways_data["test-gateway"]["target_url"] == "https://test.example.com"

    def test_generate_gateways_json_replaces_cids(self, temp_project_with_gateways):
        """Test that generate_gateways_json replaces file paths with CIDs."""
        generator = BootImageGenerator(temp_project_with_gateways)
        generator.ensure_cids_directory()

        generator.generate_gateways_json()

        # Verify gateways.json was created
        gateways_json_path = temp_project_with_gateways / "reference_templates" / "gateways.json"
        with open(gateways_json_path, "r", encoding="utf-8") as f:
            gateways_data = json.load(f)

        # CIDs should be replaced (start with AAAAAAA for literal or be full CID)
        request_cid = gateways_data["test-gateway"]["request_transform_cid"]
        response_cid = gateways_data["test-gateway"]["response_transform_cid"]

        assert not request_cid.startswith("reference_templates/"), (
            "Request transform CID should be replaced"
        )
        assert not response_cid.startswith("reference_templates/"), (
            "Response transform CID should be replaced"
        )

    def test_gateways_json_includes_template_cids(self, temp_project_with_gateways):
        """Generated gateways.json should replace template file paths with CIDs."""
        generator = BootImageGenerator(temp_project_with_gateways)
        generator.ensure_cids_directory()

        gateways_cid = generator.generate_gateways_json()
        assert gateways_cid

        gateways_json_path = temp_project_with_gateways / "reference_templates" / "gateways.json"
        assert gateways_json_path.exists()

        gateways_data = json.loads(gateways_json_path.read_text())
        templates = gateways_data["test-gateway"].get("templates")
        assert isinstance(templates, dict)
        assert set(templates.keys()) == {"test_page.html", "test_error.html"}

        # Should be CIDs, not reference_templates paths
        assert templates["test_page.html"].startswith("AAAAA")
        assert templates["test_error.html"].startswith("AAAAA")

    def test_gateways_variable_in_boot_json(self, temp_project_with_gateways):
        """Test that gateways variable is properly set in boot.json."""
        generator = BootImageGenerator(temp_project_with_gateways)

        generator.generate()

        # Verify boot.json was created
        boot_json_path = temp_project_with_gateways / "reference_templates" / "boot.json"
        assert boot_json_path.exists()

        with open(boot_json_path, "r", encoding="utf-8") as f:
            boot_data = json.load(f)

        # Find gateways variable
        gateways_var = None
        for var in boot_data["variables"]:
            if var["name"] == "gateways":
                gateways_var = var
                break

        assert gateways_var is not None, "gateways variable should exist in boot.json"
        assert gateways_var["enabled"] is True
        # The definition should be replaced with a CID, not GENERATED:gateways.json
        assert gateways_var["definition"] != "GENERATED:gateways.json", (
            "gateways definition should be replaced with CID"
        )

    def test_gateways_in_default_boot_json(self, temp_project_with_gateways):
        """Test that gateways are included in default.boot.json."""
        generator = BootImageGenerator(temp_project_with_gateways)

        generator.generate()

        # Verify default.boot.json was created
        default_boot_path = temp_project_with_gateways / "reference_templates" / "default.boot.json"
        assert default_boot_path.exists()

        with open(default_boot_path, "r", encoding="utf-8") as f:
            boot_data = json.load(f)

        # Find gateways variable
        gateways_var = None
        for var in boot_data["variables"]:
            if var["name"] == "gateways":
                gateways_var = var
                break

        assert gateways_var is not None, "gateways variable should exist in default.boot.json"

    def test_gateways_in_readonly_boot_json(self, temp_project_with_gateways):
        """Test that gateways are included in readonly.boot.json."""
        generator = BootImageGenerator(temp_project_with_gateways)

        generator.generate()

        # Verify readonly.boot.json was created
        readonly_boot_path = temp_project_with_gateways / "reference_templates" / "readonly.boot.json"
        assert readonly_boot_path.exists()

        with open(readonly_boot_path, "r", encoding="utf-8") as f:
            boot_data = json.load(f)

        # Find gateways variable
        gateways_var = None
        for var in boot_data["variables"]:
            if var["name"] == "gateways":
                gateways_var = var
                break

        assert gateways_var is not None, "gateways variable should exist in readonly.boot.json"

    def test_gateways_transform_files_processed(self, temp_project_with_gateways):
        """Test that transform files are processed and stored as CIDs."""
        generator = BootImageGenerator(temp_project_with_gateways)

        generator.generate()

        # Verify transform files were processed
        assert "reference_templates/gateways/transforms/test_request.py" in generator.processed_files
        assert "reference_templates/gateways/transforms/test_response.py" in generator.processed_files

    def test_gateways_cid_in_result(self, temp_project_with_gateways):
        """Test that generate() returns gateways_cid in result."""
        generator = BootImageGenerator(temp_project_with_gateways)

        result = generator.generate()

        # Result should include gateways_cid
        assert "gateways_cid" in result, "Result should include gateways_cid"
        assert len(result["gateways_cid"]) >= 8, "gateways_cid should be a valid CID"
