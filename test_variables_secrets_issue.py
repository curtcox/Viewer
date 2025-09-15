#!/usr/bin/env python3
"""
Unit tests to demonstrate the variables and secrets issue with server execution
"""
import sys
import unittest
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, '.')

# Mock all dependencies before importing
sys.modules['app'] = Mock()
sys.modules['models'] = Mock()
sys.modules['forms'] = Mock()
sys.modules['auth_providers'] = Mock()
sys.modules['text_function_runner'] = Mock()

# Mock Flask imports
flask_mock = Mock()
flask_mock.render_template = Mock()
flask_mock.flash = Mock()
flask_mock.redirect = Mock()
flask_mock.url_for = Mock()
flask_mock.request = Mock()
flask_mock.session = Mock()
flask_mock.make_response = Mock()
flask_mock.abort = Mock()
sys.modules['flask'] = flask_mock

# Mock flask_login
flask_login_mock = Mock()
sys.modules['flask_login'] = flask_login_mock

# Import the functions we want to test
from routes import user_variables, user_secrets, build_request_args  # noqa: E402

class TestVariablesSecretsIssue(unittest.TestCase):
    """Test cases to demonstrate the variables and secrets serialization issue"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_app = Mock()
        
    def tearDown(self):
        """Clean up test environment"""
        pass
    
    @patch('routes.current_user')
    @patch('routes.get_user_variables')
    def test_user_variables_returns_model_objects(self, mock_get_vars, mock_current_user):
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
        
        mock_get_vars.return_value = [mock_var1, mock_var2]
        
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
    @patch('routes.get_user_secrets')
    def test_user_secrets_returns_model_objects(self, mock_get_secrets, mock_current_user):
        """Test that user_secrets() returns SQLAlchemy model objects, not serializable data"""
        # Mock current user
        mock_current_user.id = 'test_user_123'
        
        # Create mock Secret objects
        mock_secret1 = Mock()
        mock_secret1.name = 'test_secret1'
        mock_secret1.definition = 'secret_value1'
        mock_secret1.user_id = 'test_user_123'
        
        mock_get_secrets.return_value = [mock_secret1]
        
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
        
        # Mock request context
        with patch('routes.request') as mock_request:
            mock_request.path = '/echo1'
            mock_request.method = 'GET'
            mock_request.headers = {}
            
            # Call build_request_args
            args = build_request_args()
            
            # Check that variables and secrets are included in args.context
            self.assertIsInstance(args['context']['variables'], dict)
            self.assertIsInstance(args['context']['secrets'], dict)
            
            # Check that the dictionary contains the expected key-value pairs
            self.assertEqual(args['context']['variables']['test_var'], 'test_value')
            self.assertEqual(args['context']['secrets']['test_secret'], 'secret_value')


if __name__ == '__main__':
    unittest.main()
