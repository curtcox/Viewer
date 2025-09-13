#!/usr/bin/env python3
"""
Unit tests to demonstrate the variables and secrets issue with server execution
"""
import sys
import unittest
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, '.')

# Import Flask app and models
from app import app
from routes import user_variables, user_secrets, build_request_args

class TestVariablesSecretsIssue(unittest.TestCase):
    """Test cases to demonstrate the variables and secrets serialization issue"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    @patch('routes.current_user')
    @patch('routes.Variable')
    def test_user_variables_returns_model_objects(self, mock_variable_class, mock_current_user):
        """Test that user_variables() returns SQLAlchemy model objects, not serializable data"""
        # Mock current user
        mock_current_user.id = 'test_user_123'
        
        # Create mock Variable objects
        mock_var1 = Mock()
        mock_var1.name = 'test_var1'
        mock_var1.definition = 'value1'
        mock_var1.user_id = 'test_user_123'
        
        mock_var2 = Mock()
        mock_var2.name = 'test_var2'
        mock_var2.definition = 'value2'
        mock_var2.user_id = 'test_user_123'
        
        # Mock the query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_var1, mock_var2]
        mock_variable_class.query = mock_query
        
        # Call the function
        result = user_variables()
        
        # Verify it returns model objects, not serializable data
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Mock)  # Should be model object
        self.assertIsInstance(result[1], Mock)  # Should be model object
        
        # These objects are NOT JSON serializable
        with self.assertRaises((TypeError, AttributeError)):
            import json
            json.dumps(result)
        
        print(f"user_variables() returned: {result}")
        print(f"Type of first item: {type(result[0])}")
        print(f"First item has name: {hasattr(result[0], 'name')}")
        print(f"First item has definition: {hasattr(result[0], 'definition')}")
    
    @patch('routes.current_user')
    @patch('routes.Secret')
    def test_user_secrets_returns_model_objects(self, mock_secret_class, mock_current_user):
        """Test that user_secrets() returns SQLAlchemy model objects, not serializable data"""
        # Mock current user
        mock_current_user.id = 'test_user_123'
        
        # Create mock Secret objects
        mock_secret1 = Mock()
        mock_secret1.name = 'test_secret1'
        mock_secret1.definition = 'secret_value1'
        mock_secret1.user_id = 'test_user_123'
        
        # Mock the query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_secret1]
        mock_secret_class.query = mock_query
        
        # Call the function
        result = user_secrets()
        
        # Verify it returns model objects, not serializable data
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Mock)  # Should be model object
        
        # These objects are NOT JSON serializable
        with self.assertRaises((TypeError, AttributeError)):
            import json
            json.dumps(result)
        
        print(f"user_secrets() returned: {result}")
        print(f"Type of first item: {type(result[0])}")
        print(f"First item has name: {hasattr(result[0], 'name')}")
        print(f"First item has definition: {hasattr(result[0], 'definition')}")
    
    @patch('routes.user_variables')
    @patch('routes.user_secrets')
    @patch('routes.user_servers')
    def test_build_request_args_with_model_objects(self, mock_user_servers, mock_user_secrets, mock_user_variables):
        """Test that build_request_args includes model objects instead of serializable data"""
        # Mock variables and secrets to return model objects
        mock_var = Mock()
        mock_var.name = 'test_var'
        mock_var.definition = 'test_value'
        mock_user_variables.return_value = [mock_var]
        
        mock_secret = Mock()
        mock_secret.name = 'test_secret'
        mock_secret.definition = 'secret_value'
        mock_user_secrets.return_value = [mock_secret]
        
        mock_user_servers.return_value = []
        
        # Use Flask test client to create proper request context
        with self.app.test_client() as client:
            with client.application.test_request_context('/echo1'):
                # Call build_request_args within request context
                args = build_request_args()
                
                # Check that variables and secrets are converted to dictionaries by model_as_dict
                self.assertIsInstance(args['variables'], dict)
                self.assertIsInstance(args['secrets'], dict)
                
                # Check that the dictionary contains the expected key-value pairs
                self.assertEqual(args['variables']['test_var'], 'test_value')
                self.assertEqual(args['secrets']['test_secret'], 'secret_value')
                
                print(f"Variables in args: {args['variables']}")
                print(f"Secrets in args: {args['secrets']}")
                
                # This demonstrates that the data is properly serializable
                args_str = str(args)
                print(f"String representation of args: {args_str}")
                
                # The variables and secrets should show their actual data, not model representations
                self.assertIn('test_var', args_str)
                self.assertIn('test_value', args_str)
                self.assertIn('test_secret', args_str)
                self.assertIn('secret_value', args_str)
    
    def test_what_echo1_server_should_receive(self):
        """Test what the echo1 server should actually receive for variables and secrets"""
        # This is what the echo1 server SHOULD receive
        expected_variables = [
            {'name': 'test_var1', 'definition': 'value1'},
            {'name': 'test_var2', 'definition': 'value2'}
        ]
        expected_secrets = [
            {'name': 'test_secret1', 'definition': 'secret_value1'}
        ]
        
        # These can be properly serialized
        import json
        variables_json = json.dumps(expected_variables)
        secrets_json = json.dumps(expected_secrets)
        
        print(f"Expected variables format: {expected_variables}")
        print(f"Expected secrets format: {expected_secrets}")
        print(f"Variables JSON: {variables_json}")
        print(f"Secrets JSON: {secrets_json}")
        
        # When converted to string, they show meaningful data
        variables_str = str(expected_variables)
        secrets_str = str(expected_secrets)
        
        print(f"Variables as string: {variables_str}")
        print(f"Secrets as string: {secrets_str}")
        
        # This is what should appear in the echo1 output
        self.assertIn('test_var1', variables_str)
        self.assertIn('value1', variables_str)
        self.assertIn('test_secret1', secrets_str)
        self.assertIn('secret_value1', secrets_str)

if __name__ == '__main__':
    unittest.main(verbosity=2)
