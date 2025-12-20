#!/usr/bin/env python3

import json
import os
import tempfile
import unittest

from app import create_app, db
from cid_core import is_literal_cid
from cid_utils import (
    generate_all_variable_definitions_json,
    get_current_variable_definitions_cid,
    store_variable_definitions_cid,
)
from db_access import get_cid_by_path
from models import CID, Variable
from routes.variables import update_variable_definitions_cid


class TestVariableDefinitionsCID(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database
        self.db_fd, temp_db_path = tempfile.mkstemp()
        self.db_path = temp_db_path
        config = {
            "DATABASE": temp_db_path,
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{temp_db_path}",
            "WTF_CSRF_ENABLED": False,
        }

        flask_app = create_app(config)

        self.app = flask_app.test_client()
        self.app_context = flask_app.app_context()
        self.app_context.push()

        db.create_all()

        # Create test variables
        self.variable1 = Variable(name="test_var1", definition="value1")
        self.variable2 = Variable(name="test_var2", definition="value2")
        db.session.add(self.variable1)
        db.session.add(self.variable2)
        db.session.commit()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_generate_all_variable_definitions_json_with_variables(self):
        """Test JSON generation with existing variables"""
        json_content = generate_all_variable_definitions_json()

        # Parse the JSON to verify structure
        data = json.loads(json_content)

        # Should contain both variables
        self.assertEqual(len(data), 2)
        self.assertIn("test_var1", data)
        self.assertIn("test_var2", data)
        self.assertEqual(data["test_var1"], "value1")
        self.assertEqual(data["test_var2"], "value2")

        # Verify JSON formatting (sorted keys, proper indentation)
        expected_json = json.dumps(
            {"test_var1": "value1", "test_var2": "value2"}, indent=2, sort_keys=True
        )
        self.assertEqual(json_content, expected_json)

    def test_generate_all_variable_definitions_json_empty(self):
        """Test JSON generation with no variables"""
        # Clear all variables for this test
        Variable.query.delete()
        db.session.commit()

        json_content = generate_all_variable_definitions_json()
        data = json.loads(json_content)

        # Should be empty dictionary
        self.assertEqual(data, {})
        self.assertEqual(json_content, "{}")

    def test_generate_all_variable_definitions_json_sorted(self):
        """Test that variables are sorted alphabetically in JSON"""
        # Add more variables in non-alphabetical order
        var_z = Variable(name="z_var", definition="z_value")
        var_a = Variable(name="a_var", definition="a_value")
        db.session.add(var_z)
        db.session.add(var_a)
        db.session.commit()

        json_content = generate_all_variable_definitions_json()
        data = json.loads(json_content)

        # Keys should be in alphabetical order
        keys = list(data.keys())
        self.assertEqual(keys, ["a_var", "test_var1", "test_var2", "z_var"])

    def test_store_variable_definitions_cid(self):
        """Test storing variable definitions as CID"""
        cid = store_variable_definitions_cid()

        # Should return a valid CID string
        self.assertIsInstance(cid, str)
        self.assertTrue(len(cid) > 0)

        # CID should resolve correctly (via DB for hash-based or literal extraction)
        cid_record = get_cid_by_path(f"/{cid}")
        self.assertIsNotNone(cid_record)

        # Verify the stored/embedded content matches expected JSON
        expected_json = generate_all_variable_definitions_json()
        stored_content = cid_record.file_data.decode("utf-8")
        self.assertEqual(stored_content, expected_json)

    def test_store_variable_definitions_cid_deduplication(self):
        """Test that identical content doesn't create duplicate CIDs"""
        # Store CID first time
        cid1 = store_variable_definitions_cid()

        # Store again with same content
        cid2 = store_variable_definitions_cid()

        # Should return same CID
        self.assertEqual(cid1, cid2)

        # For literal CIDs, no DB record should exist; for hash-based, only one
        if not is_literal_cid(cid1):
            cid_records = CID.query.filter_by(path=f"/{cid1}").all()
            self.assertEqual(len(cid_records), 1)

    def test_get_current_variable_definitions_cid_existing(self):
        """Test getting CID when it already exists"""
        # First store a CID
        original_cid = store_variable_definitions_cid()

        # Get current CID should return the same one
        current_cid = get_current_variable_definitions_cid()
        self.assertEqual(current_cid, original_cid)

    def test_get_current_variable_definitions_cid_create_if_missing(self):
        """Test that CID is created if it doesn't exist"""
        # Get CID without storing first
        cid = get_current_variable_definitions_cid()

        # Should return a valid CID
        self.assertIsInstance(cid, str)
        self.assertTrue(len(cid) > 0)

        # CID should resolve correctly
        cid_record = get_cid_by_path(f"/{cid}")
        self.assertIsNotNone(cid_record)

    def test_update_variable_definitions_cid(self):
        """Test updating CID after variable changes"""
        # Store initial CID
        original_cid = store_variable_definitions_cid()

        # Add a new variable
        new_var = Variable(name="new_var", definition="new_value")
        db.session.add(new_var)
        db.session.commit()

        # Update CID
        updated_cid = update_variable_definitions_cid()

        # Should be different from original
        self.assertNotEqual(updated_cid, original_cid)

        # New CID should resolve correctly and contain the new variable
        cid_record = get_cid_by_path(f"/{updated_cid}")
        stored_content = cid_record.file_data.decode("utf-8")
        data = json.loads(stored_content)
        self.assertIn("new_var", data)
        self.assertEqual(data["new_var"], "new_value")

    def test_cid_content_deterministic(self):
        """Test that same variable content produces same CID"""
        # Create additional variables with same content
        var1_copy = Variable(name="test_var1_copy", definition="value1")
        var2_copy = Variable(name="test_var2_copy", definition="value2")
        db.session.add(var1_copy)
        db.session.add(var2_copy)
        db.session.commit()

        # Should get same CID for identical content
        cid1 = store_variable_definitions_cid()
        cid2 = store_variable_definitions_cid()

        self.assertEqual(cid1, cid2)

    def test_cid_uniqueness_per_content(self):
        """Test that different variable content produces different CIDs"""
        # Store CID for current variables
        cid1 = store_variable_definitions_cid()

        # Modify a variable
        self.variable1.definition = "modified_value1"
        db.session.commit()

        # Store CID again
        cid2 = store_variable_definitions_cid()

        # Should be different CIDs
        self.assertNotEqual(cid1, cid2)


if __name__ == "__main__":
    unittest.main()
