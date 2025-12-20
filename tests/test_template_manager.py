"""Tests for template_manager module."""

import json
import os
import unittest

# Configure environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-secret-key"
os.environ["TESTING"] = "True"

from app import app
from models import Variable, CID, db
from template_manager import (
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
    ENTITY_TYPE_UPLOADS,
    get_templates_config,
    validate_templates_json,
    get_template_status,
    get_templates_for_type,
    get_template_by_key,
    resolve_cid_value,
)


class TestTemplateManager(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        # Sample valid templates structure
        self.valid_templates = {
            "aliases": {
                "template1": {
                    "name": "Template Alias 1",
                    "description": "Test alias template",
                    "target_path_cid": "AAAABBBB",
                    "metadata": {
                        "created": "2025-01-01T00:00:00Z",
                        "author": "testuser",
                    },
                }
            },
            "servers": {
                "template2": {
                    "name": "Template Server 1",
                    "description": "Test server template",
                    "definition_cid": "CCCCDDDD",
                    "metadata": {},
                }
            },
            "variables": {},
            "secrets": {},
            "uploads": {
                "template3": {
                    "name": "Template Upload 1",
                    "description": "Test upload template",
                    "content": "Sample upload content",
                    "metadata": {},
                }
            },
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_templates_config_no_variable(self):
        """Test when templates variable doesn't exist."""
        result = get_templates_config()
        self.assertIsNone(result)

    def test_get_templates_config_empty_variable(self):
        """Test when templates variable is empty."""
        var = Variable(
            name="templates",
            definition="",
        )
        db.session.add(var)
        db.session.commit()

        result = get_templates_config()
        self.assertIsNone(result)

    def test_get_templates_config_direct_json(self):
        """Test parsing direct JSON from templates variable."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        result = get_templates_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)
        self.assertIn("servers", result)
        self.assertEqual(result["aliases"]["template1"]["name"], "Template Alias 1")

    def test_get_templates_config_cid_reference(self):
        """Test parsing templates from CID reference."""
        # Create CID record
        cid_data = json.dumps(self.valid_templates).encode("utf-8")
        cid_record = CID(
            path="/TESTCID123",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        # Create templates variable with CID reference
        var = Variable(
            name="templates",
            definition="TESTCID123",
        )
        db.session.add(var)
        db.session.commit()

        result = get_templates_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)
        self.assertEqual(result["aliases"]["template1"]["name"], "Template Alias 1")

    def test_get_templates_config_cid_with_slash(self):
        """Test parsing templates from CID reference with leading slash."""
        cid_data = json.dumps(self.valid_templates).encode("utf-8")
        cid_record = CID(
            path="/TESTCID456",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        var = Variable(
            name="templates",
            definition="/TESTCID456",
        )
        db.session.add(var)
        db.session.commit()

        result = get_templates_config()
        self.assertIsNotNone(result)
        self.assertIn("aliases", result)

    def test_get_templates_config_invalid_json(self):
        """Test handling of invalid JSON."""
        var = Variable(
            name="templates",
            definition="not valid json {{{",
        )
        db.session.add(var)
        db.session.commit()

        result = get_templates_config()
        self.assertIsNone(result)

    def test_validate_templates_json_valid(self):
        """Test validation of valid templates JSON."""
        json_str = json.dumps(self.valid_templates)
        is_valid, error = validate_templates_json(json_str)

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_templates_json_empty(self):
        """Test validation of empty string."""
        is_valid, error = validate_templates_json("")

        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_validate_templates_json_invalid_json(self):
        """Test validation of invalid JSON."""
        is_valid, error = validate_templates_json("not json")

        self.assertFalse(is_valid)
        self.assertIn("Invalid JSON", error)

    def test_validate_templates_json_not_dict(self):
        """Test validation when JSON is not a dictionary."""
        is_valid, error = validate_templates_json('["array"]')

        self.assertFalse(is_valid)
        self.assertIn("object", error.lower())

    def test_validate_templates_json_missing_key(self):
        """Test validation when missing required key."""
        incomplete = {
            "aliases": {},
            "servers": {},
            # Missing 'variables', 'secrets', and 'uploads'
        }
        is_valid, error = validate_templates_json(json.dumps(incomplete))

        self.assertFalse(is_valid)
        self.assertIn("Missing required key", error)

    def test_validate_templates_json_wrong_type_for_entity(self):
        """Test validation when entity type is not a dict."""
        invalid = {
            "aliases": [],  # Should be dict
            "servers": {},
            "variables": {},
            "secrets": {},
            "uploads": {},
        }
        is_valid, error = validate_templates_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("must be an object", error)

    def test_validate_templates_json_template_missing_name(self):
        """Test validation when template is missing name field."""
        invalid = {
            "aliases": {"template1": {"description": "No name field"}},
            "servers": {},
            "variables": {},
            "secrets": {},
            "uploads": {},
        }
        is_valid, error = validate_templates_json(json.dumps(invalid))

        self.assertFalse(is_valid)
        self.assertIn("missing", error.lower())
        self.assertIn("name", error.lower())

    def test_get_template_status_no_templates(self):
        """Test status when no templates exist."""
        status = get_template_status()

        self.assertFalse(status["is_valid"])
        self.assertEqual(status["count_total"], 0)
        self.assertEqual(status["count_by_type"]["aliases"], 0)

    def test_get_template_status_valid_templates(self):
        """Test status with valid templates."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        status = get_template_status()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["count_total"], 3)
        self.assertEqual(status["count_by_type"]["aliases"], 1)
        self.assertEqual(status["count_by_type"]["servers"], 1)
        self.assertEqual(status["count_by_type"]["variables"], 0)
        self.assertEqual(status["count_by_type"]["secrets"], 0)
        self.assertEqual(status["count_by_type"]["uploads"], 1)

    def test_get_templates_for_type_aliases(self):
        """Test getting templates for aliases type."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_templates_for_type(ENTITY_TYPE_ALIASES)

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["key"], "template1")
        self.assertEqual(templates[0]["name"], "Template Alias 1")

    def test_get_templates_for_type_servers(self):
        """Test getting templates for servers type."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_templates_for_type(ENTITY_TYPE_SERVERS)

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["key"], "template2")
        self.assertEqual(templates[0]["name"], "Template Server 1")

    def test_get_templates_for_type_empty(self):
        """Test getting templates for type with no templates."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_templates_for_type(ENTITY_TYPE_VARIABLES)

        self.assertEqual(len(templates), 0)

    def test_get_templates_for_type_invalid_type(self):
        """Test getting templates for invalid entity type."""
        templates = get_templates_for_type("invalid_type")

        self.assertEqual(len(templates), 0)

    def test_get_template_by_key_found(self):
        """Test getting specific template by key."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        template = get_template_by_key(ENTITY_TYPE_ALIASES, "template1")

        self.assertIsNotNone(template)
        self.assertEqual(template["key"], "template1")
        self.assertEqual(template["name"], "Template Alias 1")

    def test_get_template_by_key_not_found(self):
        """Test getting non-existent template by key."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        template = get_template_by_key(ENTITY_TYPE_ALIASES, "nonexistent")

        self.assertIsNone(template)

    def test_get_template_by_key_invalid_type(self):
        """Test getting template with invalid entity type."""
        template = get_template_by_key("invalid_type", "template1")

        self.assertIsNone(template)

    def test_resolve_cid_value_direct_value(self):
        """Test resolve_cid_value with direct value."""
        result = resolve_cid_value("some_value")

        # Should return the original value if not a valid CID
        self.assertEqual(result, "some_value")

    def test_resolve_cid_value_cid_reference(self):
        """Test resolve_cid_value with actual CID."""
        # Create CID record
        cid_data = b"resolved content"
        cid_record = CID(
            path="/RESOLVECID",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        result = resolve_cid_value("RESOLVECID")

        self.assertEqual(result, "resolved content")

    def test_resolve_cid_value_empty(self):
        """Test resolve_cid_value with empty value."""
        result = resolve_cid_value("")

        self.assertIsNone(result)

    def test_resolve_cid_value_with_slash(self):
        """Test resolve_cid_value with leading slash."""
        cid_data = b"content with slash"
        cid_record = CID(
            path="/SLASHCID",
            file_data=cid_data,
            file_size=len(cid_data),
        )
        db.session.add(cid_record)
        db.session.commit()

        result = resolve_cid_value("/SLASHCID")

        self.assertEqual(result, "content with slash")

    def test_get_templates_for_type_uploads(self):
        """Test getting templates for uploads type."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        templates = get_templates_for_type(ENTITY_TYPE_UPLOADS)

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["key"], "template3")
        self.assertEqual(templates[0]["name"], "Template Upload 1")
        self.assertEqual(templates[0]["content"], "Sample upload content")

    def test_get_template_status_includes_uploads(self):
        """Test status includes uploads count."""
        var = Variable(
            name="templates",
            definition=json.dumps(self.valid_templates),
        )
        db.session.add(var)
        db.session.commit()

        status = get_template_status()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["count_total"], 3)
        self.assertEqual(status["count_by_type"]["uploads"], 1)


if __name__ == "__main__":
    unittest.main()
