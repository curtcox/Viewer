import unittest
from unittest.mock import Mock, patch
import io
from app import create_app, db
from models import User
from cid_utils import CID_LENGTH, process_file_upload


class TestUploadExtensions(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create a test user
            self.test_user = User(
                id='test_user_123',
                email='test@example.com',
                first_name='Test',
                last_name='User'
            )
            db.session.add(self.test_user)
            db.session.commit()

    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_process_file_upload_returns_filename(self):
        """Test that process_file_upload returns both content and filename"""
        # Create a mock form with file data
        form = Mock()
        mock_file = Mock()
        mock_file.filename = 'test_document.pdf'
        mock_file.read.return_value = b'test file content'
        form.file.data = mock_file
        
        content, filename = process_file_upload(form)
        
        self.assertEqual(content, b'test file content')
        self.assertEqual(filename, 'test_document.pdf')

    def test_process_file_upload_handles_no_filename(self):
        """Test that process_file_upload handles files without filename"""
        # Create a mock form with file data but no filename
        form = Mock()
        mock_file = Mock()
        mock_file.filename = None
        mock_file.read.return_value = b'test file content'
        form.file.data = mock_file
        
        content, filename = process_file_upload(form)
        
        self.assertEqual(content, b'test file content')
        self.assertEqual(filename, 'upload')

    @patch('routes.uploads.current_user')
    @patch('routes.uploads.require_login')
    def test_upload_text_gets_txt_extension(self, mock_require_login, mock_current_user):
        """Test that pasted text uploads get .txt extension in view URL"""
        # Mock authentication
        mock_current_user.is_authenticated = True
        mock_current_user.id = 'test_user_123'
        mock_require_login.return_value = lambda f: f  # Bypass login requirement
        
        with self.app.app_context():
            # Mock the session to simulate logged in user
            with self.client.session_transaction() as sess:
                sess['_user_id'] = 'test_user_123'
                sess['_fresh'] = True
            
            # Simulate text upload
            response = self.client.post('/upload', data={
                'upload_type': 'text',
                'text_content': 'This is some test text content',
                'submit': 'Upload'
            }, follow_redirects=False)
            
            # Should render upload_success.html template
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Upload Successful', response.data)
            
            # Check that the response contains .txt extension in the view URL
            self.assertIn(b'.txt', response.data)

    @patch('routes.uploads.current_user')
    @patch('routes.uploads.require_login')
    def test_upload_file_preserves_original_extension(self, mock_require_login, mock_current_user):
        """Test that file uploads preserve their original extension"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 'test_user_123'
        mock_require_login.return_value = lambda f: f  # Bypass login requirement
        
        with self.app.app_context():
            # Mock the session to simulate logged in user
            with self.client.session_transaction() as sess:
                sess['_user_id'] = 'test_user_123'
                sess['_fresh'] = True
            
            # Create a mock file with .pdf extension
            file_data = io.BytesIO(b'PDF file content')
            file_data.name = 'document.pdf'
            
            # Simulate file upload
            response = self.client.post('/upload', data={
                'upload_type': 'file',
                'file': (file_data, 'document.pdf'),
                'submit': 'Upload'
            }, follow_redirects=False)
            
            # Should render upload_success.html template
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Upload Successful', response.data)
            
            # Check that the response contains .pdf extension in the view URL
            self.assertIn(b'.pdf', response.data)

    @patch('routes.uploads.current_user')
    @patch('routes.uploads.require_login')
    def test_upload_file_handles_no_extension(self, mock_require_login, mock_current_user):
        """Test that file uploads without extension don't break"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 'test_user_123'
        mock_require_login.return_value = lambda f: f  # Bypass login requirement
        
        with self.app.app_context():
            # Mock the session to simulate logged in user
            with self.client.session_transaction() as sess:
                sess['_user_id'] = 'test_user_123'
                sess['_fresh'] = True
            
            # Create a mock file without extension
            file_data = io.BytesIO(b'File content without extension')
            file_data.name = 'document'
            
            # Simulate file upload
            response = self.client.post('/upload', data={
                'upload_type': 'file',
                'file': (file_data, 'document'),
                'submit': 'Upload'
            }, follow_redirects=False)
            
            # Should render upload_success.html template
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Upload Successful', response.data)
            
            # Should not have any extension in the view URL (no .txt, .pdf, etc.)
            response_text = response.data.decode('utf-8')
            # The CID should appear without any extension and match the canonical length
            cid_pattern = rf'/[A-Za-z0-9_-]{{{CID_LENGTH}}}(?!\.)'
            self.assertRegex(response_text, cid_pattern)  # CID without extension


if __name__ == '__main__':
    unittest.main()
