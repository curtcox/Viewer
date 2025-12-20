#!/usr/bin/env python3
"""
Unit tests to demonstrate the variables and secrets issue with server execution
"""

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, ".")

from app import app
from routes.secrets import list_secrets
from routes.variables import list_variables
from server_execution import build_request_args, model_as_dict  # pylint: disable=no-name-in-module


class TestVariablesSecretsIssue(unittest.TestCase):
    """Test cases to demonstrate the variables and secrets serialization issue"""

    def setUp(self):
        """Set up test environment"""
        self.mock_app = Mock()

    def tearDown(self):
        """Clean up test environment"""

    @patch("routes.variables.get_variables")
    def test_list_variables_returns_model_objects(self, mock_get_vars):
        """Test that list_variables() returns SQLAlchemy model objects, not serializable data"""
        # Create mock Variable objects
        mock_var1 = Mock()
        mock_var1.name = "test_var1"
        mock_var1.definition = "value1"

        mock_var2 = Mock()
        mock_var2.name = "test_var2"
        mock_var2.definition = "value2"

        mock_get_vars.return_value = [mock_var1, mock_var2]

        # Call the function
        result = list_variables()

        # Verify it returns model objects, not serializable data
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Mock)  # Should be model object
        self.assertIsInstance(result[1], Mock)  # Should be model object

        # These objects are NOT JSON serializable
        with self.assertRaises((TypeError, AttributeError)):
            import json

            json.dumps(result)

        print(f"list_variables() returned: {result}")
        print(f"Type of first item: {type(result[0])}")
        print(f"First item has name: {hasattr(result[0], 'name')}")
        print(f"First item has definition: {hasattr(result[0], 'definition')}")

    @patch("routes.secrets.get_secrets")
    def test_list_secrets_returns_model_objects(self, mock_get_secrets):
        """Test that list_secrets() returns SQLAlchemy model objects, not serializable data"""
        # Create mock Secret objects
        mock_secret1 = Mock()
        mock_secret1.name = "test_secret1"
        mock_secret1.definition = "secret_value1"

        mock_get_secrets.return_value = [mock_secret1]

        # Call the function
        result = list_secrets()

        # Verify it returns model objects, not serializable data
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Mock)  # Should be model object

        # These objects are NOT JSON serializable
        with self.assertRaises((TypeError, AttributeError)):
            import json

            json.dumps(result)

        print(f"list_secrets() returned: {result}")
        print(f"Type of first item: {type(result[0])}")
        print(f"First item has name: {hasattr(result[0], 'name')}")
        print(f"First item has definition: {hasattr(result[0], 'definition')}")

    @patch("server_execution.code_execution.get_variables")
    @patch("server_execution.code_execution.get_secrets")
    @patch("server_execution.code_execution.get_servers")
    def test_build_request_args_with_model_objects(
        self, mock_servers, mock_secrets, mock_variables
    ):
        """Test that build_request_args includes model objects instead of serializable data"""
        # Mock variables and secrets to return model objects
        mock_var = Mock()
        mock_var.name = "test_var"
        mock_var.definition = "test_value"
        mock_variables.return_value = [mock_var]

        mock_secret = Mock()
        mock_secret.name = "test_secret"
        mock_secret.definition = "secret_value"
        mock_secrets.return_value = [mock_secret]

        mock_servers.return_value = []

        # Use Flask request context instead of patch.dict
        with app.test_request_context("/echo1"):
            # Call build_request_args
            args = build_request_args()

            # Check that variables and secrets are included in args.context
            self.assertIsInstance(args["context"]["variables"], dict)
            self.assertIsInstance(args["context"]["secrets"], dict)

            # Check that the dictionary contains the expected key-value pairs
            self.assertEqual(args["context"]["variables"]["test_var"], "test_value")
            self.assertEqual(args["context"]["secrets"]["test_secret"], "secret_value")

    @patch("server_execution.code_execution.get_variables")
    @patch("server_execution.code_execution.get_secrets")
    @patch("server_execution.code_execution.get_servers")
    def test_build_request_args_skips_disabled_entries(
        self,
        mock_servers,
        mock_secrets,
        mock_variables,
    ):
        mock_variables.return_value = [
            SimpleNamespace(name="active_var", definition="value", enabled=True),
            SimpleNamespace(name="inactive_var", definition="value", enabled=False),
        ]

        mock_secrets.return_value = [
            SimpleNamespace(name="active_secret", definition="value", enabled=True),
            SimpleNamespace(name="inactive_secret", definition="value", enabled=False),
        ]

        mock_servers.return_value = []

        # Use Flask request context instead of patch.dict
        with app.test_request_context("/echo1"):
            args = build_request_args()

            self.assertIn("active_var", args["context"]["variables"])
            self.assertNotIn("inactive_var", args["context"]["variables"])
            self.assertIn("active_secret", args["context"]["secrets"])
            self.assertNotIn("inactive_secret", args["context"]["secrets"])

    def test_model_as_dict_ignores_disabled_entries(self):
        entries = [
            SimpleNamespace(name="alpha", definition="A", enabled=True),
            SimpleNamespace(name="beta", definition="B", enabled=False),
        ]

        result = model_as_dict(entries)

        self.assertEqual(result, {"alpha": "A"})


if __name__ == "__main__":
    unittest.main()
