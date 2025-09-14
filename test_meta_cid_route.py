import unittest
import json
from unittest.mock import patch, Mock
from app import app, db
from models import CID, User


class TestMetaCIDRoute(unittest.TestCase):
    """Test suite for the /meta/{CID} route functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Skip test if app is mocked (running with unittest discover)
        if isinstance(app, Mock):
            self.skipTest("Skipping test due to Flask-Login conflicts when running with unittest discover")
        
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_test_user(self):
        """Helper method to create a test user"""
        test_user = User(
            id='test_user_123',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True
        )
        db.session.add(test_user)
        db.session.commit()
        return test_user
    
    def _create_test_cid(self, cid_path="bafybei123test", file_data=b"test content", user=None):
        """Helper method to create a test CID record"""
        if user is None:
            user = self._create_test_user()
        
        cid_record = CID(
            path=f"/{cid_path}",
            file_data=file_data,
            file_size=len(file_data),
            uploaded_by_user_id=user.id
        )
        db.session.add(cid_record)
        db.session.commit()
        return cid_record
    
    def test_meta_route_returns_valid_json_for_existing_cid(self):
        """Test that /meta/{CID} returns valid JSON metadata for existing CID"""
        with self.app.app_context():
            # Create test data
            test_user = self._create_test_user()
            test_content = b"Hello, World! This is test content."
            cid_record = self._create_test_cid("bafybei123valid", test_content, test_user)
            
            # Make request to meta route
            response = self.client.get(f'/meta/bafybei123valid')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify metadata structure and content
            self.assertIn('cid', data)
            self.assertIn('path', data)
            self.assertIn('file_size', data)
            self.assertIn('created_at', data)
            self.assertIn('uploaded_by_user_id', data)
            self.assertIn('uploaded_by', data)
            
            # Verify specific values
            self.assertEqual(data['cid'], 'bafybei123valid')
            self.assertEqual(data['path'], '/bafybei123valid')
            self.assertEqual(data['file_size'], len(test_content))
            self.assertEqual(data['uploaded_by_user_id'], test_user.id)
            
            # Verify uploaded_by nested object
            uploaded_by = data['uploaded_by']
            self.assertEqual(uploaded_by['user_id'], test_user.id)
            self.assertEqual(uploaded_by['username'], 'Test')  # first_name
            self.assertEqual(uploaded_by['email'], test_user.email)
    
    def test_meta_route_returns_404_for_nonexistent_cid(self):
        """Test that /meta/{CID} returns 404 for non-existent CID"""
        with self.app.app_context():
            # Make request for non-existent CID
            response = self.client.get('/meta/bafybei999nonexistent')
            
            # Verify 404 response
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.content_type, 'application/json')
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify error message
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'CID not found')
    
    def test_meta_route_handles_cid_without_uploader(self):
        """Test that /meta/{CID} handles CID records without uploader information"""
        with self.app.app_context():
            # Create CID record without uploader
            cid_record = CID(
                path="/bafybei123orphan",
                file_data=b"orphaned content",
                file_size=16,
                uploaded_by_user_id=None  # No uploader
            )
            db.session.add(cid_record)
            db.session.commit()
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123orphan')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify metadata
            self.assertEqual(data['cid'], 'bafybei123orphan')
            self.assertEqual(data['path'], '/bafybei123orphan')
            self.assertEqual(data['file_size'], 16)
            self.assertIsNone(data['uploaded_by_user_id'])
            
            # Verify uploaded_by is not present when no uploader
            self.assertNotIn('uploaded_by', data)
    
    def test_meta_route_handles_cid_with_deleted_user(self):
        """Test that /meta/{CID} handles CID records where uploader user was deleted"""
        with self.app.app_context():
            # Create user and CID, then delete user
            test_user = self._create_test_user()
            cid_record = self._create_test_cid("bafybei123deleted", b"content from deleted user", test_user)
            
            # Delete the user (simulating user deletion)
            db.session.delete(test_user)
            db.session.commit()
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123deleted')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify metadata
            self.assertEqual(data['cid'], 'bafybei123deleted')
            # When user is deleted, uploaded_by_user_id becomes None due to foreign key constraints
            self.assertIsNone(data['uploaded_by_user_id'])
            
            # Verify uploaded_by is not present when user is deleted
            self.assertNotIn('uploaded_by', data)
    
    def test_meta_route_returns_iso_formatted_datetime(self):
        """Test that created_at is returned in ISO format"""
        with self.app.app_context():
            # Create test CID
            cid_record = self._create_test_cid("bafybei123datetime", b"datetime test content")
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123datetime')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify created_at is in ISO format
            self.assertIn('created_at', data)
            created_at = data['created_at']
            
            # Should be able to parse as ISO datetime
            from datetime import datetime
            try:
                parsed_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                self.assertIsInstance(parsed_datetime, datetime)
            except ValueError:
                self.fail(f"created_at '{created_at}' is not in valid ISO format")
    
    def test_meta_route_handles_large_file_size(self):
        """Test that /meta/{CID} correctly reports file size for large files"""
        with self.app.app_context():
            # Create CID with large content
            large_content = b"x" * 1024 * 1024  # 1MB of data
            cid_record = self._create_test_cid("bafybei123large", large_content)
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123large')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify file size is correct
            self.assertEqual(data['file_size'], 1024 * 1024)
    
    def test_meta_route_handles_empty_file(self):
        """Test that /meta/{CID} handles empty files correctly"""
        with self.app.app_context():
            # Create CID with empty content
            empty_content = b""
            cid_record = self._create_test_cid("bafybei123empty", empty_content)
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123empty')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify file size is 0
            self.assertEqual(data['file_size'], 0)
    
    def test_meta_route_handles_special_characters_in_cid(self):
        """Test that /meta/{CID} handles CIDs with valid special characters"""
        with self.app.app_context():
            # Create CID with special characters (valid base32 characters)
            special_cid = "bafybei234567abcdefghijklmnopqrstuvwxyz234567"
            cid_record = self._create_test_cid(special_cid, b"special char content")
            
            # Make request to meta route
            response = self.client.get(f'/meta/{special_cid}')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify CID is returned correctly
            self.assertEqual(data['cid'], special_cid)
            self.assertEqual(data['path'], f'/{special_cid}')
    
    def test_meta_route_json_response_structure(self):
        """Test that /meta/{CID} returns exactly the expected JSON structure"""
        with self.app.app_context():
            # Create test data with all fields
            test_user = self._create_test_user()
            cid_record = self._create_test_cid("bafybei123structure", b"structure test", test_user)
            
            # Make request to meta route
            response = self.client.get('/meta/bafybei123structure')
            
            # Parse JSON response
            data = json.loads(response.data)
            
            # Verify exact structure - should have these keys and no others
            expected_keys = {'cid', 'path', 'file_size', 'created_at', 'uploaded_by_user_id', 'uploaded_by'}
            actual_keys = set(data.keys())
            self.assertEqual(actual_keys, expected_keys)
            
            # Verify uploaded_by structure
            uploaded_by_keys = set(data['uploaded_by'].keys())
            expected_uploaded_by_keys = {'user_id', 'username', 'email'}
            self.assertEqual(uploaded_by_keys, expected_uploaded_by_keys)
    
    def test_meta_route_no_authentication_required(self):
        """Test that /meta/{CID} does not require authentication"""
        with self.app.app_context():
            # Create CID without authentication
            cid_record = self._create_test_cid("bafybei123public", b"public content")
            
            # Make request without any authentication
            response = self.client.get('/meta/bafybei123public')
            
            # Should succeed without authentication
            self.assertEqual(response.status_code, 200)
            
            # Parse JSON response
            data = json.loads(response.data)
            self.assertEqual(data['cid'], 'bafybei123public')


if __name__ == '__main__':
    unittest.main()
