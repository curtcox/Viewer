import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys
import os

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the Flask app and other dependencies before importing routes
class MockApp:
    def __init__(self):
        self.config = {'TESTING': True}
    
    def test_request_context(self, path, **kwargs):
        return MockRequestContext(path, **kwargs)

class MockRequestContext:
    def __init__(self, path, headers=None):
        self.path = path
        self.headers = headers or {}
    
    def __enter__(self):
        # Mock the request object
        import routes
        routes.request = Mock()
        routes.request.path = self.path
        routes.request.headers = Mock()
        routes.request.headers.get = lambda key, default=None: self.headers.get(key, default)
        return self
    
    def __exit__(self, *args):
        pass

# Mock all the dependencies
sys.modules['app'] = Mock()
sys.modules['models'] = Mock()
sys.modules['forms'] = Mock()
sys.modules['auth_providers'] = Mock()
sys.modules['text_function_runner'] = Mock()

# Mock Flask imports
from unittest.mock import Mock
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

# Now we can import the function we want to test
from routes import serve_cid_content


class TestServeCidContent(unittest.TestCase):
    """Test suite for serve_cid_content function content disposition header behavior"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = MockApp()
        self.app.config['TESTING'] = True
        
        # Create mock CID content object
        self.mock_cid_content = Mock()
        self.mock_cid_content.file_data = b"test content"
        self.mock_cid_content.created_at = datetime.now(timezone.utc)
        
    def test_cid_only_no_content_disposition(self):
        """Test /{CID} - should not set content disposition header"""
        path = "/bafybeihelloworld123456789012345678901234567890123456"
        
        with self.app.test_request_context(path):
            with patch('routes.make_response') as mock_make_response:
                mock_response = Mock()
                mock_response.headers = {}
                mock_make_response.return_value = mock_response
                
                result = serve_cid_content(self.mock_cid_content, path)
                
                # Should not have Content-Disposition header
                self.assertNotIn('Content-Disposition', mock_response.headers)
                
    def test_cid_with_extension_no_content_disposition(self):
        """Test /{CID}.{ext} - should not set content disposition header"""
        test_cases = [
            "/bafybeihelloworld123456789012345678901234567890123456.txt",
            "/bafybeihelloworld123456789012345678901234567890123456.html",
            "/bafybeihelloworld123456789012345678901234567890123456.json",
            "/bafybeihelloworld123456789012345678901234567890123456.pdf",
        ]
        
        for path in test_cases:
            with self.subTest(path=path):
                with self.app.test_request_context(path):
                    with patch('routes.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        result = serve_cid_content(self.mock_cid_content, path)
                        
                        # Should not have Content-Disposition header
                        self.assertNotIn('Content-Disposition', mock_response.headers)

    def test_cid_with_filename_sets_content_disposition(self):
        """Test /{CID}.{filename}.{ext} - should set content disposition header with filename"""
        test_cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.document.txt", "document.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.report.pdf", "report.pdf"),
            ("/bafybeihelloworld123456789012345678901234567890123456.data.json", "data.json"),
            ("/bafybeihelloworld123456789012345678901234567890123456.page.html", "page.html"),
            ("/bafybeihelloworld123456789012345678901234567890123456.my-file.csv", "my-file.csv"),
            ("/bafybeihelloworld123456789012345678901234567890123456.test_file.py", "test_file.py"),
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, filename=expected_filename):
                with self.app.test_request_context(path):
                    with patch('routes.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        result = serve_cid_content(self.mock_cid_content, path)
                        
                        # Should have Content-Disposition header with correct filename
                        expected_header = f'attachment; filename="{expected_filename}"'
                        self.assertEqual(mock_response.headers.get('Content-Disposition'), expected_header)

    def test_cid_with_multiple_dots_in_filename(self):
        """Test /{CID}.{filename.with.dots}.{ext} - should handle filenames with multiple dots"""
        test_cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.my.data.file.txt", "my.data.file.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.version.1.2.3.json", "version.1.2.3.json"),
            ("/bafybeihelloworld123456789012345678901234567890123456.backup.2024.01.15.sql", "backup.2024.01.15.sql"),
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, filename=expected_filename):
                with self.app.test_request_context(path):
                    with patch('routes.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        result = serve_cid_content(self.mock_cid_content, path)
                        
                        # Should have Content-Disposition header with correct filename
                        expected_header = f'attachment; filename="{expected_filename}"'
                        self.assertEqual(mock_response.headers.get('Content-Disposition'), expected_header)

    def test_edge_cases(self):
        """Test edge cases for path parsing"""
        # Test very short CID-like paths
        test_cases = [
            ("/abc.txt", None),  # Too short to be CID, no filename
            ("/abc.document.txt", "document.txt"),  # Short but has filename pattern
            ("/a.b.c", "b.c"),  # Multiple dots, should extract filename
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, filename=expected_filename):
                with self.app.test_request_context(path):
                    with patch('routes.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        result = serve_cid_content(self.mock_cid_content, path)
                        
                        if expected_filename:
                            expected_header = f'attachment; filename="{expected_filename}"'
                            self.assertEqual(mock_response.headers.get('Content-Disposition'), expected_header)
                        else:
                            self.assertNotIn('Content-Disposition', mock_response.headers)

    def test_filename_with_special_characters(self):
        """Test filenames with special characters are properly escaped"""
        test_cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.file with spaces.txt", "file with spaces.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.file-with-dashes.txt", "file-with-dashes.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.file_with_underscores.txt", "file_with_underscores.txt"),
        ]
        
        for path, expected_filename in test_cases:
            with self.subTest(path=path, filename=expected_filename):
                with self.app.test_request_context(path):
                    with patch('routes.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        result = serve_cid_content(self.mock_cid_content, path)
                        
                        # Should have Content-Disposition header with correct filename
                        expected_header = f'attachment; filename="{expected_filename}"'
                        self.assertEqual(mock_response.headers.get('Content-Disposition'), expected_header)

    def test_none_content_returns_none(self):
        """Test that None content returns None"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.txt"
        
        with self.app.test_request_context(path):
            result = serve_cid_content(None, path)
            self.assertIsNone(result)

    def test_content_with_none_file_data_returns_none(self):
        """Test that content with None file_data returns None"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.txt"
        mock_content = Mock()
        mock_content.file_data = None
        
        with self.app.test_request_context(path):
            result = serve_cid_content(mock_content, path)
            self.assertIsNone(result)

    def test_caching_headers_still_work(self):
        """Test that caching headers are still properly set"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.document.txt"
        
        with self.app.test_request_context(path):
            with patch('routes.make_response') as mock_make_response:
                mock_response = Mock()
                mock_response.headers = {}
                mock_make_response.return_value = mock_response
                
                result = serve_cid_content(self.mock_cid_content, path)
                
                # Should have caching headers
                self.assertIn('ETag', mock_response.headers)
                self.assertIn('Cache-Control', mock_response.headers)
                self.assertIn('Last-Modified', mock_response.headers)
                
                # Should also have Content-Disposition
                self.assertIn('Content-Disposition', mock_response.headers)

    def test_conditional_requests_with_filename(self):
        """Test that conditional requests work properly even with filename paths"""
        path = "/bafybeihelloworld123456789012345678901234567890123456.document.txt"
        
        # Test If-None-Match
        with self.app.test_request_context(path, headers={'If-None-Match': '"bafybeihelloworld123456789012345678901234567890123456"'}):
            with patch('routes.make_response') as mock_make_response:
                mock_response = Mock()
                mock_response.headers = {}
                mock_make_response.return_value = mock_response
                
                result = serve_cid_content(self.mock_cid_content, path)
                
                # Should return 304 response
                mock_make_response.assert_called_with('', 304)


if __name__ == '__main__':
    unittest.main()
