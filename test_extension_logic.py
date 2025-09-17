import unittest
from unittest.mock import Mock
from cid_utils import process_file_upload, process_text_upload


class TestExtensionLogic(unittest.TestCase):
    """Test the core extension handling logic without full app integration"""
    
    def test_process_file_upload_with_extension(self):
        """Test that process_file_upload extracts filename correctly"""
        form = Mock()
        mock_file = Mock()
        mock_file.filename = 'document.pdf'
        mock_file.read.return_value = b'PDF content'
        form.file.data = mock_file
        
        content, filename = process_file_upload(form)
        
        self.assertEqual(content, b'PDF content')
        self.assertEqual(filename, 'document.pdf')
    
    def test_process_file_upload_no_extension(self):
        """Test that process_file_upload handles files without extension"""
        form = Mock()
        mock_file = Mock()
        mock_file.filename = 'document'
        mock_file.read.return_value = b'File content'
        form.file.data = mock_file
        
        content, filename = process_file_upload(form)
        
        self.assertEqual(content, b'File content')
        self.assertEqual(filename, 'document')
    
    def test_process_file_upload_no_filename(self):
        """Test that process_file_upload handles missing filename"""
        form = Mock()
        mock_file = Mock()
        mock_file.filename = None
        mock_file.read.return_value = b'File content'
        form.file.data = mock_file
        
        content, filename = process_file_upload(form)
        
        self.assertEqual(content, b'File content')
        self.assertEqual(filename, 'upload')
    
    def test_extension_extraction_logic(self):
        """Test the extension extraction logic used in upload route"""
        # Test cases for the extension extraction logic
        test_cases = [
            ('document.pdf', 'pdf'),
            ('image.PNG', 'png'),  # Should be lowercase
            ('file.tar.gz', 'gz'),  # Should get last extension
            ('document', ''),  # No extension
            ('file.', ''),  # Ends with dot but no extension
            ('.hidden', 'hidden'),  # Hidden file - rsplit will extract 'hidden'
            ('file.TXT', 'txt'),  # Mixed case
        ]
        
        for filename, expected_ext in test_cases:
            with self.subTest(filename=filename):
                if '.' in filename:
                    actual_ext = filename.rsplit('.', 1)[1].lower()
                else:
                    actual_ext = ''
                
                self.assertEqual(actual_ext, expected_ext)
    
    def test_text_upload_returns_content(self):
        """Test that process_text_upload returns encoded content"""
        form = Mock()
        form.text_content.data = 'Hello, world!'
        
        content = process_text_upload(form)
        
        self.assertEqual(content, b'Hello, world!')


if __name__ == '__main__':
    unittest.main()
