# pylint: disable=no-member
# This test file works extensively with Flask-SQLAlchemy models which have
# dynamically generated attributes (query, session, etc.) that pylint cannot detect
import base64
import hashlib
import re
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cid_utils
from app import app, db
from cid_utils import (
    CID_LENGTH,
    CID_NORMALIZED_PATTERN,
    _looks_like_markdown,
    encode_cid_length,
    generate_cid,
    get_mime_type_from_extension,
    is_normalized_cid,
    serve_cid_content,
)
from db_access import create_cid_record
from models import CID


class TestCIDFunctionality(unittest.TestCase):
    """Test suite for the new simplified CID functionality"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_test_user(self, user_id: str = 'test_user_123'):
        """Helper method to provide a lightweight user-like object."""

        return SimpleNamespace(id=user_id)

    def test_generate_cid_only_uses_file_data(self):
        """Test that CID generation only uses file data, not MIME type"""
        file_data = b"Hello, World!"

        # Generate CID
        cid = generate_cid(file_data)

        # Verify CID format matches the canonical specification
        self.assertEqual(len(cid), CID_LENGTH)
        self.assertTrue(CID_NORMALIZED_PATTERN.fullmatch(cid))
        self.assertTrue(is_normalized_cid(cid))

        # Verify CID is deterministic (same input = same output)
        cid2 = generate_cid(file_data)
        self.assertEqual(cid, cid2)

        # Verify different data produces different CID
        different_data = b"Hello, Universe!"
        different_cid = generate_cid(different_data)
        self.assertNotEqual(cid, different_cid)

    def test_generate_cid_matches_expected_hash(self):
        """Test that CID generation produces expected hash"""
        file_data = b"test content"

        # Calculate expected CID manually
        length_prefix = encode_cid_length(len(file_data))
        digest = hashlib.sha512(file_data).digest()
        digest_part = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        expected_cid = f"{length_prefix}{digest_part}"

        # Generate CID using function
        actual_cid = generate_cid(file_data)

        self.assertEqual(actual_cid, expected_cid)

    def test_get_mime_type_from_extension(self):
        """Test MIME type detection from file extensions"""
        test_cases = [
            # No extension should return default
            ('/bafybei123', 'application/octet-stream'),

            # Common text types
            ('/bafybei123.txt', 'text/plain'),
            ('/bafybei123.html', 'text/html'),
            ('/bafybei123.htm', 'text/html'),
            ('/bafybei123.css', 'text/css'),
            ('/bafybei123.js', 'application/javascript'),
            ('/bafybei123.json', 'application/json'),
            ('/bafybei123.xml', 'application/xml'),
            ('/bafybei123.md', 'text/markdown'),
            ('/bafybei123.csv', 'text/csv'),

            # Images
            ('/bafybei123.jpg', 'image/jpeg'),
            ('/bafybei123.jpeg', 'image/jpeg'),
            ('/bafybei123.png', 'image/png'),
            ('/bafybei123.gif', 'image/gif'),
            ('/bafybei123.svg', 'image/svg+xml'),
            ('/bafybei123.webp', 'image/webp'),
            ('/bafybei123.ico', 'image/x-icon'),

            # Audio/Video
            ('/bafybei123.mp3', 'audio/mpeg'),
            ('/bafybei123.wav', 'audio/wav'),
            ('/bafybei123.mp4', 'video/mp4'),
            ('/bafybei123.webm', 'video/webm'),

            # Archives
            ('/bafybei123.zip', 'application/zip'),
            ('/bafybei123.tar', 'application/x-tar'),
            ('/bafybei123.gz', 'application/gzip'),
            ('/bafybei123.pdf', 'application/pdf'),

            # Programming languages
            ('/bafybei123.py', 'text/x-python'),
            ('/bafybei123.java', 'text/x-java-source'),
            ('/bafybei123.c', 'text/x-c'),
            ('/bafybei123.cpp', 'text/x-c++'),
            ('/bafybei123.h', 'text/x-c'),
            ('/bafybei123.hpp', 'text/x-c++'),

            # Case insensitive
            ('/bafybei123.HTML', 'text/html'),
            ('/bafybei123.PNG', 'image/png'),
            ('/bafybei123.PDF', 'application/pdf'),

            # Unknown extension should return default
            ('/bafybei123.unknown', 'application/octet-stream'),
        ]

        for path, expected_mime in test_cases:
            with self.subTest(path=path):
                actual_mime = get_mime_type_from_extension(path)
                self.assertEqual(actual_mime, expected_mime)

    def test_create_cid_record_with_all_fields(self):
        """Test creating CID record with all required fields"""
        with self.app.app_context():
            test_user = self._create_test_user()
            file_content = b"Test file content for CID record"
            cid = generate_cid(file_content)

            # Create CID record
            cid_record = create_cid_record(
                cid=cid,
                file_content=file_content,
                user_id=test_user.id
            )
            # Verify record properties
            self.assertEqual(cid_record.path, f"/{cid}")
            self.assertEqual(cid_record.file_data, file_content)
            self.assertEqual(cid_record.file_size, len(file_content))
            self.assertEqual(cid_record.uploaded_by_user_id, test_user.id)

            # Verify fields that should NOT exist
            self.assertFalse(hasattr(cid_record, 'content'))
            self.assertFalse(hasattr(cid_record, 'title'))
            self.assertFalse(hasattr(cid_record, 'content_type'))
            self.assertFalse(hasattr(cid_record, 'updated_at'))

    @patch('cid_utils.make_response')
    def test_serve_cid_content_with_extension(self, mock_make_response):
        """Test serving CID content with file extension for MIME type detection"""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                # Create test CID record
                file_content = b"<html><body>Hello World</body></html>"
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                # Mock response
                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                # Test serving with .html extension
                path_with_extension = f"/{cid}.html"
                serve_cid_content(cid_record, path_with_extension)

                # Verify response was created with correct content
                mock_make_response.assert_called_once_with(file_content)

                # Verify correct MIME type was set
                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/html')

                # Verify other headers
                mock_response.headers.__setitem__.assert_any_call('Content-Length', len(file_content))
                mock_response.headers.__setitem__.assert_any_call('Cache-Control', 'public, max-age=31536000, immutable')

    @patch('cid_utils.make_response')
    def test_serve_cid_content_without_extension(self, mock_make_response):
        """Test serving CID content without extension defaults to UTF-8 text when possible."""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                # Create test CID record
                file_content = b"Binary data content"
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                # Mock response
                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                # Test serving without extension
                path_without_extension = f"/{cid}"
                serve_cid_content(cid_record, path_without_extension)

                # Verify response was created with correct content
                mock_make_response.assert_called_once_with(file_content)

                # Verify default MIME type was set for decoded text
                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/plain; charset=utf-8')

    @patch('cid_utils.make_response')
    def test_serve_cid_content_with_txt_extension(self, mock_make_response):
        """CID content requested with .txt extension should render as UTF-8 text when possible."""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                file_content = "Line one\nLine two".encode('utf-8')
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                path_with_txt = f"/{cid}.txt"
                serve_cid_content(cid_record, path_with_txt)

                mock_make_response.assert_called_once_with(file_content)
                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/plain; charset=utf-8')

    @patch('cid_utils.make_response')
    def test_serve_cid_content_without_extension_plain_python_not_rendered(self, mock_make_response):
        """Plain source files without Markdown cues should not be rendered."""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                file_content = (
                    "if __name__ == '__main__':\n"
                    "    print('hello world')\n"
                ).encode('utf-8')
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                serve_cid_content(cid_record, f"/{cid}")

                mock_make_response.assert_called_once_with(file_content)
                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/plain; charset=utf-8')

    @patch('cid_utils.make_response')
    def test_serve_cid_content_without_extension_renders_markdown(self, mock_make_response):
        """Markdown content without an extension should render to HTML."""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                markdown_body = (
                    "# Sample Document\n\n"
                    "Welcome to the **CID Markdown renderer** showcase.\n\n"
                    "- item one\n"
                    "- item two\n\n"
                    "```python\nprint('hello world')\n```\n"
                ).encode('utf-8')
                cid = generate_cid(markdown_body)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=markdown_body,
                    file_size=len(markdown_body),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                path_without_extension = f"/{cid}"
                serve_cid_content(cid_record, path_without_extension)

                mock_make_response.assert_called_once()
                rendered_bytes = mock_make_response.call_args[0][0]
                self.assertIsInstance(rendered_bytes, bytes)
                rendered_html = rendered_bytes.decode('utf-8')
                self.assertIn('<h1', rendered_html)
                self.assertIn('<ul>', rendered_html)
                self.assertIn('class="language-python"', rendered_html)

                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/html')
                mock_response.headers.__setitem__.assert_any_call('Content-Length', len(rendered_bytes))

    @patch('cid_utils._generate_qr_data_url')
    @patch('cid_utils.make_response')
    def test_serve_cid_content_qr_request_renders_qr_page(self, mock_make_response, mock_generate_qr_data_url):
        """Requests with a .qr extension should render a QR code landing page."""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                file_content = b"QR content placeholder"
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                mock_response = MagicMock()
                mock_make_response.return_value = mock_response
                sample_png_base64 = (
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
                )
                mock_generate_qr_data_url.return_value = f"data:image/png;base64,{sample_png_base64}"

                serve_cid_content(cid_record, f"/{cid}.qr")

                mock_make_response.assert_called_once()
                rendered_payload = mock_make_response.call_args[0][0]
                self.assertIsInstance(rendered_payload, (bytes, bytearray))
                rendered_html = rendered_payload.decode('utf-8')

                self.assertIn('View CID as QR Code', rendered_html)
                self.assertIn('<img', rendered_html)
                self.assertIn('data:image/png;base64,', rendered_html)
                data_url_match = re.search(r'src=\"(data:image/png;base64,[^\"]+)\"', rendered_html)
                self.assertIsNotNone(data_url_match)
                _, encoded = data_url_match.group(1).split(',', 1)
                image_bytes = base64.b64decode(encoded)
                self.assertTrue(image_bytes.startswith(b'\x89PNG\r\n\x1a\n'))

                mock_response.headers.__setitem__.assert_any_call('Content-Type', 'text/html; charset=utf-8')
                mock_response.headers.__setitem__.assert_any_call('Content-Length', len(rendered_payload))

    def test_generate_qr_data_url_uses_qrcode_module(self):
        """The QR code helper should build PNG data using the qrcode library API."""

        sample_png_base64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
        )
        sample_png_bytes = base64.b64decode(sample_png_base64)
        call_log = {}

        class FakeImage:
            def save(self, buffer, img_format):
                call_log['format'] = img_format
                buffer.write(sample_png_bytes)

        class FakeQRCode:
            def __init__(self, *, box_size=12, border=4):
                call_log['init'] = {'box_size': box_size, 'border': border}

            def add_data(self, value):
                call_log['data'] = value

            def make(self, fit=True):
                call_log['fit'] = fit

            def make_image(self, *, fill_color="black", back_color="white"):
                call_log['colors'] = {'fill': fill_color, 'back': back_color}
                return FakeImage()

        fake_module = SimpleNamespace(QRCode=FakeQRCode)

        target_url = 'https://256t.org/example'

        with patch('cid_utils.qrcode', fake_module), patch('cid_utils._qrcode_import_error', None):
            data_url = cid_utils._generate_qr_data_url(target_url)

        self.assertEqual(
            call_log['init'],
            {'box_size': 12, 'border': 4},
        )
        self.assertEqual(call_log['data'], target_url)
        self.assertTrue(call_log['fit'])
        self.assertEqual(
            call_log['colors'],
            {'fill': 'black', 'back': 'white'},
        )
        self.assertEqual(call_log['format'], 'PNG')
        self.assertEqual(
            data_url,
            f'data:image/png;base64,{sample_png_base64}',
        )

    @patch('cid_utils.make_response')
    def test_serve_cid_content_caching_headers(self, mock_make_response):
        """Test that proper caching headers are set for CID content"""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                # Create test CID record
                file_content = b"Test content for caching"
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                # Mock response
                mock_response = MagicMock()
                mock_make_response.return_value = mock_response

                # Test serving content
                serve_cid_content(cid_record, f"/{cid}.txt")

                # Verify caching headers are set
                expected_etag = f'"{cid}"'
                mock_response.headers.__setitem__.assert_any_call('ETag', expected_etag)
                mock_response.headers.__setitem__.assert_any_call('Cache-Control', 'public, max-age=31536000, immutable')
                mock_response.headers.__setitem__.assert_any_call('Expires', 'Thu, 31 Dec 2037 23:55:55 GMT')

    @patch('cid_utils.make_response')
    def test_serve_cid_content_etag_caching(self, mock_make_response):
        """Test ETag-based caching returns 304 when content hasn't changed"""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context(headers={'If-None-Match': '"test_etag"'}):
                # Create test CID record
                file_content = b"Cached content"
                cid = generate_cid(file_content)

                cid_record = CID(
                    path=f"/{cid}",
                    file_data=file_content,
                    file_size=len(file_content),
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                # Mock 304 response
                mock_304_response = MagicMock()
                mock_make_response.return_value = mock_304_response

                # Test serving content with matching ETag (use the actual CID as ETag)
                expected_etag = f'"{cid}"'
                with self.app.test_request_context(headers={'If-None-Match': expected_etag}):
                    serve_cid_content(cid_record, f"/{cid}.txt")

                    # Verify 304 response was created
                    mock_make_response.assert_called_once_with('', 304)
                    mock_304_response.headers.__setitem__.assert_called_with('ETag', expected_etag)

    def test_cid_model_simplified_fields(self):
        """Test that CID model only has the required fields"""
        with self.app.app_context():
            test_user = self._create_test_user()
            # Create a CID record
            file_content = b"Model test content"
            cid = generate_cid(file_content)

            cid_record = CID(
                path=f"/{cid}",
                file_data=file_content,
                file_size=len(file_content),
                uploaded_by_user_id=test_user.id
            )
            db.session.add(cid_record)
            db.session.commit()

            # Verify required fields exist
            self.assertIsNotNone(cid_record.id)
            self.assertEqual(cid_record.path, f"/{cid}")
            self.assertEqual(cid_record.file_data, file_content)
            self.assertEqual(cid_record.file_size, len(file_content))
            self.assertEqual(cid_record.uploaded_by_user_id, test_user.id)
            self.assertIsNotNone(cid_record.created_at)

            # Verify removed fields don't exist
            with self.assertRaises(AttributeError):
                _ = cid_record.content

            with self.assertRaises(AttributeError):
                _ = cid_record.title

            with self.assertRaises(AttributeError):
                _ = cid_record.content_type

            with self.assertRaises(AttributeError):
                _ = cid_record.updated_at

    def test_serve_cid_content_with_none_file_data_returns_none(self):
        """Test that serving CID content with None file_data returns None (fixed behavior)"""
        with self.app.app_context():
            test_user = self._create_test_user()
            with self.app.test_request_context():
                # Create a CID record with valid file_data first
                cid_record = CID(
                    path="/bafybei123",
                    file_data=b"test content",  # Valid data initially
                    file_size=12,
                    uploaded_by_user_id=test_user.id
                )
                db.session.add(cid_record)
                db.session.commit()

                # Now simulate corrupted data by setting file_data to None directly
                # (this simulates what might happen with database corruption)
                cid_record.file_data = None

                # This should now return None instead of raising TypeError
                result = serve_cid_content(cid_record, "/bafybei123.txt")
                self.assertIsNone(result)

    def test_serve_cid_content_with_none_cid_record_returns_none(self):
        """Test that serving None CID record returns None"""
        with self.app.app_context():
            # This should return None when cid_content is None
            result = serve_cid_content(None, "/bafybei123.txt")
            self.assertIsNone(result)

    def test_markdown_heuristic_balances_inline_and_structural_cues(self):
        text = "Intro paragraph.\n\n- first item\n- second item\n\nUse `code` with **bold** emphasis."
        self.assertTrue(_looks_like_markdown(text))

    def test_markdown_heuristic_ignores_plain_python_text(self):
        text = "if __name__ == '__main__':\n    print('hello world')"
        self.assertFalse(_looks_like_markdown(text))


if __name__ == '__main__':
    unittest.main()
