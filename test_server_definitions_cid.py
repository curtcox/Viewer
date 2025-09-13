import unittest
import json
import sys
from unittest.mock import Mock, patch

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

# Mock SQLAlchemy
sqlalchemy_mock = Mock()
sys.modules['sqlalchemy'] = sqlalchemy_mock

# Now import the functions we want to test
from routes import (  # noqa: E402
    generate_all_server_definitions_json,
    store_server_definitions_cid,
    get_current_server_definitions_cid,
    update_server_definitions_cid
)


class TestServerDefinitionsCID(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Mock database and models
        self.mock_db = Mock()
        self.mock_user = Mock()
        self.mock_user.id = 'test_user_123'
        
        self.mock_server1 = Mock()
        self.mock_server1.name = 'hello_world'
        self.mock_server1.definition = 'print("Hello World")'
        self.mock_server1.user_id = 'test_user_123'
        
        self.mock_server2 = Mock()
        self.mock_server2.name = 'api_server'
        self.mock_server2.definition = 'def handle_request():\n    return {"status": "ok"}'
        self.mock_server2.user_id = 'test_user_123'

    def tearDown(self):
        """Clean up after tests"""
        pass

    @patch('routes.Server')
    def test_generate_all_server_definitions_json(self, mock_server_class):
        """Test generating JSON of all server definitions for a user"""
        # Mock the full query chain: Server.query.filter_by(user_id=user_id).order_by(Server.name).all()
        mock_all = Mock()
        mock_all.all.return_value = [self.mock_server1, self.mock_server2]
        
        mock_order_by = Mock()
        mock_order_by.return_value = mock_all
        
        mock_filter_by = Mock()
        mock_filter_by.order_by = mock_order_by
        
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_filter_by
        
        mock_server_class.query = mock_query
        mock_server_class.name = Mock()  # For order_by
        
        json_data = generate_all_server_definitions_json('test_user_123')
        
        # Parse the JSON to verify structure
        data = json.loads(json_data)
        
        # Should contain both servers
        self.assertIn('hello_world', data)
        self.assertIn('api_server', data)
        
        # Check server definitions
        self.assertEqual(data['hello_world'], 'print("Hello World")')
        self.assertEqual(data['api_server'], 'def handle_request():\n    return {"status": "ok"}')
        
        # Should be valid JSON
        self.assertIsInstance(data, dict)

    @patch('routes.Server')
    def test_generate_all_server_definitions_json_empty(self, mock_server_class):
        """Test generating JSON when user has no servers"""
        # Mock the full query chain for empty result
        mock_all = Mock()
        mock_all.all.return_value = []
        
        mock_order_by = Mock()
        mock_order_by.return_value = mock_all
        
        mock_filter_by = Mock()
        mock_filter_by.order_by = mock_order_by
        
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_filter_by
        
        mock_server_class.query = mock_query
        mock_server_class.name = Mock()  # For order_by
        
        json_data = generate_all_server_definitions_json('empty_user_123')
        data = json.loads(json_data)
        
        # Should be empty dict
        self.assertEqual(data, {})

    @patch('routes.generate_cid')
    @patch('routes.CID')
    @patch('routes.db')
    @patch('routes.generate_all_server_definitions_json')
    def test_store_server_definitions_cid(self, mock_json_gen, mock_db, mock_cid_class, mock_generate_cid):
        """Test storing server definitions JSON as CID"""
        # Mock the JSON generation
        mock_json_gen.return_value = '{"hello_world": "print(\\"Hello World\\")"}'
        
        # Mock CID generation
        mock_generate_cid.return_value = 'bafybeihelloworld123456789012345678901234567890123456'
        
        # Mock CID creation
        mock_cid_instance = Mock()
        mock_cid_class.return_value = mock_cid_instance
        
        cid_path = store_server_definitions_cid('test_user_123')
        
        # Should return a CID path
        self.assertIsInstance(cid_path, str)
        self.assertTrue(len(cid_path) > 0)

    @patch('routes.generate_all_server_definitions_json')
    @patch('routes.store_server_definitions_cid')
    @patch('routes.CID')
    @patch('routes.generate_cid')
    def test_get_current_server_definitions_cid(self, mock_generate_cid, mock_cid_class, mock_store_cid, mock_generate_json):
        """Test retrieving current server definitions CID"""
        # Mock the JSON generation
        mock_generate_json.return_value = '{"test": "data"}'
        
        # Mock generate_cid to return a predictable CID
        mock_generate_cid.return_value = 'test_cid_123'
        
        # Mock CID query to return existing CID
        mock_existing_cid = Mock()
        mock_cid_query = Mock()
        mock_cid_query.filter_by.return_value.first.return_value = mock_existing_cid
        mock_cid_class.query = mock_cid_query
        
        cid_path = get_current_server_definitions_cid('test_user_123')
        self.assertIsNotNone(cid_path)
        self.assertIsInstance(cid_path, str)
        
    @patch('routes.store_server_definitions_cid')
    def test_update_server_definitions_cid(self, mock_store_cid):
        """Test updating server definitions CID when servers change"""
        # Mock the store function to return different CIDs
        mock_store_cid.return_value = 'bafybeihelloworld123456789012345678901234567890123456'
        
        # Should call store function to update CID
        update_server_definitions_cid('test_user_123')
        mock_store_cid.assert_called_once_with('test_user_123')


if __name__ == '__main__':
    unittest.main()
