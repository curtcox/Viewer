"""Regression tests for URL upload helpers."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

import requests

from cid_utils import process_url_upload


class TestProcessUrlUpload(TestCase):
    """Exercise streaming, validation, and error handling for URL uploads."""

    def _make_form(self, url: str):
        return SimpleNamespace(url=SimpleNamespace(data=url))

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_streams_chunks_and_detects_mime(self, mock_get):
        form = self._make_form(' https://example.com/download ')

        response = Mock()
        response.headers = {
            'content-type': 'text/plain; charset=utf-8',
        }
        response.iter_content.return_value = [b'Hello ', b'World']
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        content, mime_type = process_url_upload(form)

        self.assertEqual(content, b'Hello World')
        self.assertEqual(mime_type, 'text/plain')
        mock_get.assert_called_once_with(
            'https://example.com/download',
            timeout=30,
            headers=ANY,
            stream=True,
        )
        self.assertIn('Mozilla/5.0', mock_get.call_args.kwargs['headers']['User-Agent'])

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_rejects_files_over_100_mb(self, mock_get):
        form = self._make_form('https://example.com/too-big.bin')

        response = Mock()
        response.headers = {
            'content-type': 'application/octet-stream',
            'content-length': str(101 * 1024 * 1024),
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        with self.assertRaisesRegex(ValueError, 'File too large'):
            process_url_upload(form)

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_wraps_request_exceptions(self, mock_get):
        form = self._make_form('https://example.com/fail')
        mock_get.side_effect = requests.exceptions.RequestException('boom')

        with self.assertRaisesRegex(ValueError, 'Failed to download from URL: boom'):
            process_url_upload(form)

    @patch('upload_handlers.requests.get')
    def test_process_url_upload_wraps_generic_errors(self, mock_get):
        form = self._make_form('https://example.com/error')

        response = Mock()
        response.headers = {'content-type': 'text/plain'}
        response.raise_for_status.return_value = None

        def explode(**_kwargs):
            raise RuntimeError('iter failure')

        response.iter_content.side_effect = explode
        mock_get.return_value = response

        with self.assertRaisesRegex(ValueError, 'Error processing URL: iter failure'):
            process_url_upload(form)

