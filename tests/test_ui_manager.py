"""Tests for ui_manager module."""

import json
import os
import unittest

# Configure environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-secret-key"
os.environ["TESTING"] = "True"

from app import app
from models import Variable, CID, db
from ui_manager import (
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
    get_uis_config,
    validate_uis_json,
    get_uis_status,
    get_uis_for_entity,
    get_ui_count_for_entity,
)


class TestUIManager(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        # Sample valid UIs structure
        self.valid_uis = {
            "aliases": {
                "my-alias": [
                    {"name": "Dashboard View", "path": "/dashboard/my-alias"},
                    {"name": "Graph View", "path": "/graph/my-alias"},
                ]
            },
            "servers": {
                "my-server": [
                    {"name": "Debug UI", "path": "/debug/my-server"},
                ]
            },
            "variables": {
                "my-variable": [
                    {"name": "Editor", "path": "/edit/my-variable"},
                    {"name": "Viewer", "path": "/view/my-variable"},
                    {"name": "History", "path": "/history/my-variable"},
                ]
            },
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_uis_config_no_variable(self):
        """Test when uis variable doesn't exist."""
        result = get_uis_config()
        self.assertIsNone(result)

    def test_get_uis_config_empty_variable(self):
        """Test when uis variable is empty."""
        var = Variable(
            name="uis",
            definition="",
        )
        db.session.add(var)
        db.session.commit()

        result = get_uis_config()
        self.assertIsNone(result)

    def test_get_uis_config_direct_json(self):
        """Test parsing direct JSON from uis variable."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        result = get_uis_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)
        self.assertIn("servers", result)
        self.assertIn("variables", result)
        self.assertEqual(len(result["aliases"]["my-alias"]), 2)

    def test_get_uis_config_cid_reference(self):
        """Test parsing uis from CID reference."""
        # Create CID record
        cid_data = json.dumps(self.valid_uis).encode("utf-8")
        cid_record = CID(
            path="/TESTCID123",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        # Create uis variable with CID reference
        var = Variable(
            name="uis",
            definition="TESTCID123",
        )
        db.session.add(var)
        db.session.commit()

        result = get_uis_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)
        self.assertEqual(result["aliases"]["my-alias"][0]["name"], "Dashboard View")

    def test_get_uis_config_cid_with_slash(self):
        """Test parsing uis from CID reference with leading slash."""
        cid_data = json.dumps(self.valid_uis).encode("utf-8")
        cid_record = CID(
            path="/TESTCID456",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        var = Variable(
            name="uis",
            definition="/TESTCID456",
        )
        db.session.add(var)
        db.session.commit()

        result = get_uis_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)

    def test_get_uis_config_invalid_json(self):
        """Test handling of invalid JSON."""
        var = Variable(
            name="uis",
            definition="not valid json {{{",
        )
        db.session.add(var)
        db.session.commit()

        result = get_uis_config()
        self.assertIsNone(result)

    def test_validate_uis_json_valid(self):
        """Test validation of valid UIs JSON."""
        json_str = json.dumps(self.valid_uis)
        is_valid, error = validate_uis_json(json_str)

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_uis_json_empty(self):
        """Test validation of empty string."""
        is_valid, error = validate_uis_json("")

        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_validate_uis_json_invalid_json(self):
        """Test validation of invalid JSON."""
        is_valid, error = validate_uis_json("not json")

        self.assertFalse(is_valid)
        self.assertIn("Invalid JSON", error)

    def test_validate_uis_json_not_dict(self):
        """Test validation when JSON is not a dictionary."""
        is_valid, error = validate_uis_json('["array"]')

        self.assertFalse(is_valid)
        self.assertIn("object", error.lower())

    def test_validate_uis_json_entity_type_not_dict(self):
        """Test validation when entity type is not a dict."""
        invalid = {
            "aliases": [],  # Should be dict
            "servers": {},
            "variables": {},
        }
        is_valid, error = validate_uis_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("must be an object", error)

    def test_validate_uis_json_uis_not_array(self):
        """Test validation when UIs for entity is not an array."""
        invalid = {
            "aliases": {
                "my-alias": {"name": "test"}  # Should be array
            }
        }
        is_valid, error = validate_uis_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("must be an array", error)

    def test_validate_uis_json_ui_missing_name(self):
        """Test validation when UI is missing name field."""
        invalid = {
            "aliases": {
                "my-alias": [
                    {"path": "/test"}  # Missing 'name'
                ]
            }
        }
        is_valid, error = validate_uis_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("missing 'name' field", error)

    def test_validate_uis_json_ui_missing_path(self):
        """Test validation when UI is missing path field."""
        invalid = {
            "aliases": {
                "my-alias": [
                    {"name": "Test UI"}  # Missing 'path'
                ]
            }
        }
        is_valid, error = validate_uis_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("missing 'path' field", error)

    def test_validate_uis_json_empty_object(self):
        """Test validation of empty object (valid)."""
        is_valid, error = validate_uis_json("{}")

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_uis_json_partial_entity_types(self):
        """Test validation with only some entity types (valid)."""
        partial = {
            "aliases": {"my-alias": [{"name": "Test", "path": "/test"}]}
            # No servers or variables - should be OK
        }
        is_valid, error = validate_uis_json(json.dumps(partial))

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_get_uis_status_no_uis(self):
        """Test status when no UIs exist."""
        status = get_uis_status()

        self.assertFalse(status["is_valid"])
        self.assertEqual(status["count_total"], 0)
        self.assertEqual(status["count_by_type"]["aliases"], 0)

    def test_get_uis_status_valid_uis(self):
        """Test status with valid UIs."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        status = get_uis_status()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["count_total"], 3)  # 1 alias + 1 server + 1 variable
        self.assertEqual(status["count_by_type"]["aliases"], 1)
        self.assertEqual(status["count_by_type"]["servers"], 1)
        self.assertEqual(status["count_by_type"]["variables"], 1)

    def test_get_uis_for_entity_existing(self):
        """Test getting UIs for an existing entity."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        uis = get_uis_for_entity(ENTITY_TYPE_ALIASES, "my-alias")

        self.assertEqual(len(uis), 2)
        self.assertEqual(uis[0]["name"], "Dashboard View")
        self.assertEqual(uis[0]["path"], "/dashboard/my-alias")
        self.assertEqual(uis[1]["name"], "Graph View")
        self.assertEqual(uis[1]["path"], "/graph/my-alias")

    def test_get_uis_for_entity_servers(self):
        """Test getting UIs for servers type."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        uis = get_uis_for_entity(ENTITY_TYPE_SERVERS, "my-server")

        self.assertEqual(len(uis), 1)
        self.assertEqual(uis[0]["name"], "Debug UI")
        self.assertEqual(uis[0]["path"], "/debug/my-server")

    def test_get_uis_for_entity_variables(self):
        """Test getting UIs for variables type."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        uis = get_uis_for_entity(ENTITY_TYPE_VARIABLES, "my-variable")

        self.assertEqual(len(uis), 3)
        self.assertEqual(uis[0]["name"], "Editor")
        self.assertEqual(uis[2]["name"], "History")

    def test_get_uis_for_entity_not_found(self):
        """Test getting UIs for non-existent entity."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        uis = get_uis_for_entity(ENTITY_TYPE_ALIASES, "nonexistent")

        self.assertEqual(len(uis), 0)

    def test_get_uis_for_entity_invalid_type(self):
        """Test getting UIs for invalid entity type."""
        uis = get_uis_for_entity("invalid_type", "my-alias")

        self.assertEqual(len(uis), 0)

    def test_get_uis_for_entity_no_config(self):
        """Test getting UIs when no config exists."""
        uis = get_uis_for_entity(ENTITY_TYPE_ALIASES, "my-alias")

        self.assertEqual(len(uis), 0)

    def test_get_ui_count_for_entity(self):
        """Test counting UIs for an entity."""
        var = Variable(
            name="uis",
            definition=json.dumps(self.valid_uis),
        )
        db.session.add(var)
        db.session.commit()

        count = get_ui_count_for_entity(ENTITY_TYPE_ALIASES, "my-alias")
        self.assertEqual(count, 2)

        count = get_ui_count_for_entity(ENTITY_TYPE_SERVERS, "my-server")
        self.assertEqual(count, 1)

        count = get_ui_count_for_entity(ENTITY_TYPE_VARIABLES, "my-variable")
        self.assertEqual(count, 3)

        count = get_ui_count_for_entity(ENTITY_TYPE_ALIASES, "nonexistent")
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
