"""Unit tests for upload_handlers module."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from upload_handlers import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    MAX_UPLOAD_SIZE_BYTES,
    URL_DOWNLOAD_TIMEOUT_SECONDS,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)


class TestConstants(unittest.TestCase):
    """Tests for module constants."""

    def test_constants_defined(self):
        """Test that constants are defined with reasonable values."""
        self.assertEqual(MAX_UPLOAD_SIZE_BYTES, 100 * 1024 * 1024)
        self.assertEqual(DOWNLOAD_CHUNK_SIZE_BYTES, 8192)
        self.assertEqual(URL_DOWNLOAD_TIMEOUT_SECONDS, 30)


class TestProcessFileUpload(unittest.TestCase):
    """Tests for process_file_upload function."""

    def test_process_file_upload_with_filename(self):
        """Test processing file upload with filename."""
        mock_file = Mock()
        mock_file.read.return_value = b"test content"
        mock_file.filename = "test.txt"

        mock_form = SimpleNamespace(file=SimpleNamespace(data=mock_file))

        content, filename = process_file_upload(mock_form)
        self.assertEqual(content, b"test content")
        self.assertEqual(filename, "test.txt")

    def test_process_file_upload_without_filename(self):
        """Test processing file upload without filename."""
        mock_file = Mock()
        mock_file.read.return_value = b"content"
        mock_file.filename = None

        mock_form = SimpleNamespace(file=SimpleNamespace(data=mock_file))

        content, filename = process_file_upload(mock_form)
        self.assertEqual(content, b"content")
        self.assertEqual(filename, "upload")


class TestProcessTextUpload(unittest.TestCase):
    """Tests for process_text_upload function."""

    def test_process_text_upload(self):
        """Test processing text upload."""
        mock_form = SimpleNamespace(text_content=SimpleNamespace(data="Hello, World!"))

        content = process_text_upload(mock_form)
        self.assertEqual(content, b"Hello, World!")

    def test_process_text_upload_unicode(self):
        """Test processing text upload with Unicode characters."""
        mock_form = SimpleNamespace(text_content=SimpleNamespace(data="Hello 世界! 🌍"))

        content = process_text_upload(mock_form)
        self.assertIn(b"Hello", content)
        # Verify UTF-8 encoding
        self.assertEqual(content.decode('utf-8'), "Hello 世界! 🌍")


class TestProcessURLUpload(unittest.TestCase):
    """Tests for process_url_upload function."""

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_success(self, mock_get):
        """Test successful URL upload."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            'content-type': 'text/plain; charset=utf-8',
            'content-length': '100'
        }
        mock_response.iter_content.return_value = [b"test ", b"content"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/file.txt"))

        content, mime_type = process_url_upload(mock_form)
        self.assertEqual(content, b"test content")
        self.assertEqual(mime_type, 'text/plain')

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_large_file_header(self, mock_get):
        """Test URL upload with content-length exceeding limit."""
        mock_response = Mock()
        mock_response.headers = {
            'content-type': 'application/octet-stream',
            'content-length': str(MAX_UPLOAD_SIZE_BYTES + 1)
        }
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/large.bin"))

        with self.assertRaises(ValueError) as ctx:
            process_url_upload(mock_form)
        self.assertIn("too large", str(ctx.exception))

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_large_file_streaming(self, mock_get):
        """Test URL upload that exceeds size limit during streaming."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/octet-stream'}
        # Create chunks that exceed limit
        chunk_size = MAX_UPLOAD_SIZE_BYTES // 2 + 1
        mock_response.iter_content.return_value = [b"x" * chunk_size, b"x" * chunk_size]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/huge.bin"))

        with self.assertRaises(ValueError) as ctx:
            process_url_upload(mock_form)
        self.assertIn("too large", str(ctx.exception))

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_generates_filename(self, mock_get):
        """Test that filename is generated from URL."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/png'}
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/path/image.png"))

        _, mime_type = process_url_upload(mock_form)
        self.assertEqual(mime_type, 'image/png')

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_without_filename(self, mock_get):
        """Test URL upload without filename in path."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.iter_content.return_value = [b"{}"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/api/"))

        _, mime_type = process_url_upload(mock_form)
        self.assertEqual(mime_type, 'application/json')

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_network_error(self, mock_get):
        """Test URL upload with network error."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        mock_form = SimpleNamespace(url=SimpleNamespace(data="https://example.com/error"))

        with self.assertRaises(ValueError) as ctx:
            process_url_upload(mock_form)
        self.assertIn("Failed to download", str(ctx.exception))

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_strips_url(self, mock_get):
        """Test that URL is stripped of whitespace."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/plain'}
        mock_response.iter_content.return_value = [b"test"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_form = SimpleNamespace(url=SimpleNamespace(data="  https://example.com/file.txt  "))

        process_url_upload(mock_form)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://example.com/file.txt")


if __name__ == "__main__":
    unittest.main()
