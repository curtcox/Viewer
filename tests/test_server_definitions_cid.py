import json
import unittest
from unittest.mock import Mock, patch

from cid_utils import (
    generate_all_server_definitions_json,
    get_current_server_definitions_cid,
    store_server_definitions_cid,
)
from routes.servers import update_server_definitions_cid


class TestServerDefinitionsCID(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Reset cid_storage module-level variables BEFORE test to ensure clean state
        import cid_storage
        cid_storage._get_user_servers = None
        cid_storage._get_user_variables = None
        cid_storage._get_user_secrets = None
        cid_storage._create_cid_record = None
        cid_storage._get_cid_by_path = None

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
        # Reset cid_storage module-level variables to force fresh imports in next test
        import cid_storage
        cid_storage._get_user_servers = None
        cid_storage._get_user_variables = None
        cid_storage._get_user_secrets = None
        cid_storage._create_cid_record = None
        cid_storage._get_cid_by_path = None

    @patch('db_access.get_user_servers')
    def test_generate_all_server_definitions_json(self, mock_get_servers):
        """Test generating JSON of all server definitions for a user"""
        mock_get_servers.return_value = [self.mock_server1, self.mock_server2]

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

    @patch('db_access.get_user_servers')
    def test_generate_all_server_definitions_json_empty(self, mock_get_servers):
        """Test generating JSON when user has no servers"""
        mock_get_servers.return_value = []

        json_data = generate_all_server_definitions_json('empty_user_123')
        data = json.loads(json_data)

        # Should be empty dict
        self.assertEqual(data, {})

    @patch('db_access.create_cid_record')
    @patch('db_access.get_cid_by_path')
    @patch('cid_core.generate_cid')
    @patch('cid_storage.generate_all_server_definitions_json')
    def test_store_server_definitions_cid(self, mock_json_gen, mock_generate_cid, mock_get_cid, mock_create_cid):
        """Test storing server definitions JSON as CID"""
        # Mock the JSON generation
        mock_json_gen.return_value = '{"hello_world": "print(\\"Hello World\\")"}'

        # Mock CID generation
        mock_generate_cid.return_value = 'bafybeihelloworld123456789012345678901234567890123456'

        mock_get_cid.return_value = None
        mock_create_cid.return_value = Mock()

        cid_path = store_server_definitions_cid('test_user_123')

        # Should return a CID path
        self.assertIsInstance(cid_path, str)
        self.assertTrue(len(cid_path) > 0)

    @patch('cid_storage.generate_all_server_definitions_json')
    @patch('cid_storage.store_server_definitions_cid')
    @patch('db_access.get_cid_by_path')
    @patch('cid_core.generate_cid')
    def test_get_current_server_definitions_cid(self, mock_generate_cid, mock_get_cid, mock_store_cid, mock_generate_json):
        """Test retrieving current server definitions CID"""
        # Mock the JSON generation
        mock_generate_json.return_value = '{"test": "data"}'

        # Mock generate_cid to return a predictable CID
        mock_generate_cid.return_value = 'test_cid_123'

        # Mock CID query to return existing CID
        mock_get_cid.return_value = Mock()

        cid_path = get_current_server_definitions_cid('test_user_123')
        self.assertIsNotNone(cid_path)
        self.assertIsInstance(cid_path, str)

    @patch('routes.servers.store_server_definitions_cid')
    def test_update_server_definitions_cid(self, mock_store_cid):
        """Test updating server definitions CID when servers change"""
        # Mock the store function to return different CIDs
        mock_store_cid.return_value = 'bafybeihelloworld123456789012345678901234567890123456'

        # Should call store function to update CID
        update_server_definitions_cid('test_user_123')
        mock_store_cid.assert_called_once_with('test_user_123')


if __name__ == '__main__':
    unittest.main()
