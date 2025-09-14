#!/usr/bin/env python3

import unittest
import tempfile
import os
import json
from app import app, db
from models import User, Secret, CID
from routes import (
    generate_all_secret_definitions_json,
    store_secret_definitions_cid,
    get_current_secret_definitions_cid,
    update_secret_definitions_cid,
    generate_cid
)

class TestSecretDefinitionsCID(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Skip test if app is mocked (running with unittest discover)
        from unittest.mock import Mock
        if isinstance(app, Mock):
            self.skipTest("Skipping test due to Flask-Login conflicts when running with unittest discover")
        
        # Create a temporary database
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Create test user
        self.test_user = User(id='test_user_123', email='test@example.com')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create test secrets
        self.secret1 = Secret(
            name='test_secret1',
            definition='secret_value1',
            user_id=self.test_user.id
        )
        self.secret2 = Secret(
            name='test_secret2', 
            definition='secret_value2',
            user_id=self.test_user.id
        )
        db.session.add(self.secret1)
        db.session.add(self.secret2)
        db.session.commit()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_generate_all_secret_definitions_json_with_secrets(self):
        """Test JSON generation with existing secrets"""
        json_content = generate_all_secret_definitions_json(self.test_user.id)
        
        # Parse the JSON to verify structure
        data = json.loads(json_content)
        
        # Should contain both secrets
        self.assertEqual(len(data), 2)
        self.assertIn('test_secret1', data)
        self.assertIn('test_secret2', data)
        self.assertEqual(data['test_secret1'], 'secret_value1')
        self.assertEqual(data['test_secret2'], 'secret_value2')
        
        # Verify JSON formatting (sorted keys, proper indentation)
        expected_json = json.dumps({
            'test_secret1': 'secret_value1',
            'test_secret2': 'secret_value2'
        }, indent=2, sort_keys=True)
        self.assertEqual(json_content, expected_json)

    def test_generate_all_secret_definitions_json_empty(self):
        """Test JSON generation with no secrets"""
        # Create user with no secrets
        empty_user = User(id='empty_user', email='empty@example.com')
        db.session.add(empty_user)
        db.session.commit()
        
        json_content = generate_all_secret_definitions_json(empty_user.id)
        data = json.loads(json_content)
        
        # Should be empty dictionary
        self.assertEqual(data, {})
        self.assertEqual(json_content, '{}')

    def test_generate_all_secret_definitions_json_sorted(self):
        """Test that secrets are sorted alphabetically in JSON"""
        # Add more secrets in non-alphabetical order
        secret_z = Secret(name='z_secret', definition='z_value', user_id=self.test_user.id)
        secret_a = Secret(name='a_secret', definition='a_value', user_id=self.test_user.id)
        db.session.add(secret_z)
        db.session.add(secret_a)
        db.session.commit()
        
        json_content = generate_all_secret_definitions_json(self.test_user.id)
        data = json.loads(json_content)
        
        # Keys should be in alphabetical order
        keys = list(data.keys())
        self.assertEqual(keys, ['a_secret', 'test_secret1', 'test_secret2', 'z_secret'])

    def test_store_secret_definitions_cid(self):
        """Test storing secret definitions as CID"""
        cid = store_secret_definitions_cid(self.test_user.id)
        
        # Should return a valid CID string
        self.assertIsInstance(cid, str)
        self.assertTrue(len(cid) > 0)
        
        # CID record should exist in database
        cid_record = CID.query.filter_by(path=f"/{cid}").first()
        self.assertIsNotNone(cid_record)
        self.assertEqual(cid_record.uploaded_by_user_id, self.test_user.id)
        
        # Verify the stored content matches expected JSON
        expected_json = generate_all_secret_definitions_json(self.test_user.id)
        stored_content = cid_record.file_data.decode('utf-8')
        self.assertEqual(stored_content, expected_json)

    def test_store_secret_definitions_cid_deduplication(self):
        """Test that identical content doesn't create duplicate CIDs"""
        # Store CID first time
        cid1 = store_secret_definitions_cid(self.test_user.id)
        
        # Store again with same content
        cid2 = store_secret_definitions_cid(self.test_user.id)
        
        # Should return same CID
        self.assertEqual(cid1, cid2)
        
        # Should only have one CID record
        cid_records = CID.query.filter_by(path=f"/{cid1}").all()
        self.assertEqual(len(cid_records), 1)

    def test_get_current_secret_definitions_cid_existing(self):
        """Test getting CID when it already exists"""
        # First store a CID
        original_cid = store_secret_definitions_cid(self.test_user.id)
        
        # Get current CID should return the same one
        current_cid = get_current_secret_definitions_cid(self.test_user.id)
        self.assertEqual(current_cid, original_cid)

    def test_get_current_secret_definitions_cid_create_if_missing(self):
        """Test that CID is created if it doesn't exist"""
        # Get CID without storing first
        cid = get_current_secret_definitions_cid(self.test_user.id)
        
        # Should return a valid CID
        self.assertIsInstance(cid, str)
        self.assertTrue(len(cid) > 0)
        
        # CID should exist in database
        cid_record = CID.query.filter_by(path=f"/{cid}").first()
        self.assertIsNotNone(cid_record)

    def test_update_secret_definitions_cid(self):
        """Test updating CID after secret changes"""
        # Store initial CID
        original_cid = store_secret_definitions_cid(self.test_user.id)
        
        # Add a new secret
        new_secret = Secret(name='new_secret', definition='new_value', user_id=self.test_user.id)
        db.session.add(new_secret)
        db.session.commit()
        
        # Update CID
        updated_cid = update_secret_definitions_cid(self.test_user.id)
        
        # Should be different from original
        self.assertNotEqual(updated_cid, original_cid)
        
        # New CID should contain the new secret
        cid_record = CID.query.filter_by(path=f"/{updated_cid}").first()
        stored_content = cid_record.file_data.decode('utf-8')
        data = json.loads(stored_content)
        self.assertIn('new_secret', data)
        self.assertEqual(data['new_secret'], 'new_value')

    def test_cid_content_deterministic(self):
        """Test that same secret content produces same CID"""
        # Create another user with identical secrets
        user2 = User(id='user2', email='user2@example.com')
        db.session.add(user2)
        
        secret1_copy = Secret(name='test_secret1', definition='secret_value1', user_id=user2.id)
        secret2_copy = Secret(name='test_secret2', definition='secret_value2', user_id=user2.id)
        db.session.add(secret1_copy)
        db.session.add(secret2_copy)
        db.session.commit()
        
        # Both users should get same CID for identical content
        cid1 = store_secret_definitions_cid(self.test_user.id)
        cid2 = store_secret_definitions_cid(user2.id)
        
        self.assertEqual(cid1, cid2)

    def test_cid_uniqueness_per_content(self):
        """Test that different secret content produces different CIDs"""
        # Store CID for current secrets
        cid1 = store_secret_definitions_cid(self.test_user.id)
        
        # Modify a secret
        self.secret1.definition = 'modified_secret_value1'
        db.session.commit()
        
        # Store CID again
        cid2 = store_secret_definitions_cid(self.test_user.id)
        
        # Should be different CIDs
        self.assertNotEqual(cid1, cid2)

if __name__ == '__main__':
    unittest.main()
