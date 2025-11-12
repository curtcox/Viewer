"""Unit tests for CLI functionality."""

import json
import unittest
from unittest.mock import patch

from app import create_app, db
from cli import (
    is_valid_boot_cid,
    is_valid_url,
    list_boot_cids,
    make_http_get_request,
    open_browser,
    validate_cid,
)
from cid_utils import generate_cid
from db_access import create_cid_record
from models import CID


class TestIsValidUrl(unittest.TestCase):
    """Tests for URL validation."""

    def test_valid_url_starting_with_slash(self):
        """Test URL starting with / is valid."""
        is_valid, error = is_valid_url('/dashboard')
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_valid_http_url(self):
        """Test valid http URL."""
        is_valid, error = is_valid_url('http://localhost:5001/servers')
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_valid_https_url(self):
        """Test valid https URL."""
        is_valid, error = is_valid_url('https://example.com/api/data')
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_invalid_url_no_scheme(self):
        """Test URL without scheme is invalid."""
        is_valid, error = is_valid_url('localhost:5001/dashboard')
        self.assertFalse(is_valid)
        self.assertIn('scheme', error.lower())

    def test_invalid_url_wrong_scheme(self):
        """Test URL with wrong scheme is invalid."""
        is_valid, error = is_valid_url('ftp://example.com/file')
        self.assertFalse(is_valid)
        self.assertIn('http', error.lower())

    def test_invalid_url_no_host(self):
        """Test URL without host is invalid."""
        is_valid, error = is_valid_url('http://')
        self.assertFalse(is_valid)
        self.assertIn('host', error.lower())


class TestValidateCid(unittest.TestCase):
    """Tests for CID validation."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-123'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_valid_cid_exists(self):
        """Test valid CID that exists in database."""
        with self.app.app_context():
            content = b"test content"
            cid_value = generate_cid(content)
            create_cid_record(cid_value, content, self.user_id)

            is_valid, error_type, error_msg = validate_cid(cid_value)
            self.assertTrue(is_valid)
            self.assertIsNone(error_type)
            self.assertIsNone(error_msg)

    def test_valid_cid_not_found(self):
        """Test valid CID format but not in database."""
        with self.app.app_context():
            # Generate a CID but don't store it
            content = b"non-existent content"
            cid_value = generate_cid(content)

            is_valid, error_type, error_msg = validate_cid(cid_value)
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'not_found')
            self.assertIn('not found', error_msg.lower())

    def test_invalid_cid_empty(self):
        """Test empty string is invalid CID."""
        with self.app.app_context():
            is_valid, error_type, error_msg = validate_cid('')
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'invalid_format')
            self.assertIn('empty', error_msg.lower())

    def test_invalid_cid_too_short(self):
        """Test CID that is too short."""
        with self.app.app_context():
            is_valid, error_type, error_msg = validate_cid('abc')
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'invalid_format')
            self.assertIn('short', error_msg.lower())

    def test_invalid_cid_contains_dot(self):
        """Test CID containing dot is invalid."""
        with self.app.app_context():
            is_valid, error_type, error_msg = validate_cid('AAAAAAAA.txt')
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'invalid_format')
            self.assertIn('.', error_msg)

    def test_invalid_cid_contains_slash(self):
        """Test CID containing slash is invalid."""
        with self.app.app_context():
            is_valid, error_type, error_msg = validate_cid('AAAA/AAAA')
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'invalid_format')
            self.assertIn('/', error_msg)

    def test_invalid_cid_invalid_characters(self):
        """Test CID with invalid characters."""
        with self.app.app_context():
            is_valid, error_type, error_msg = validate_cid('AAAA@@@@@')
            self.assertFalse(is_valid)
            self.assertEqual(error_type, 'invalid_format')
            self.assertIn('invalid character', error_msg.lower())


class TestIsValidBootCid(unittest.TestCase):
    """Tests for boot CID validation."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-123'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_valid_boot_cid(self):
        """Test valid boot CID (JSON object)."""
        with self.app.app_context():
            content = json.dumps({'aliases': 'AAAAAAAA', 'servers': 'AAAAAAAB'}).encode('utf-8')
            cid_value = generate_cid(content)
            record = create_cid_record(cid_value, content, self.user_id)

            is_valid, error = is_valid_boot_cid(record)
            self.assertTrue(is_valid)
            self.assertIsNone(error)

    def test_invalid_boot_cid_not_json(self):
        """Test CID with non-JSON content."""
        with self.app.app_context():
            content = b"not json content"
            cid_value = generate_cid(content)
            record = create_cid_record(cid_value, content, self.user_id)

            is_valid, error = is_valid_boot_cid(record)
            self.assertFalse(is_valid)
            self.assertIn('json', error.lower())

    def test_invalid_boot_cid_json_array(self):
        """Test CID with JSON array instead of object."""
        with self.app.app_context():
            content = json.dumps(['item1', 'item2']).encode('utf-8')
            cid_value = generate_cid(content)
            record = create_cid_record(cid_value, content, self.user_id)

            is_valid, error = is_valid_boot_cid(record)
            self.assertFalse(is_valid)
            self.assertIn('object', error.lower())

    def test_invalid_boot_cid_not_utf8(self):
        """Test CID with non-UTF8 content."""
        with self.app.app_context():
            content = b'\xff\xfe\xfd'  # Invalid UTF-8
            cid_value = generate_cid(content)
            record = create_cid_record(cid_value, content, self.user_id)

            is_valid, error = is_valid_boot_cid(record)
            self.assertFalse(is_valid)
            self.assertIn('utf-8', error.lower())

    def test_invalid_boot_cid_no_content(self):
        """Test CID with no content."""
        with self.app.app_context():
            # Create a mock CID record with no content
            record = CID(
                path='/AAAAAAAA',
                file_data=None,
                file_size=0,
                uploaded_by_user_id=self.user_id,
            )

            is_valid, error = is_valid_boot_cid(record)
            self.assertFalse(is_valid)
            self.assertIn('no content', error.lower())


class TestListBootCids(unittest.TestCase):
    """Tests for listing boot CIDs."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-123'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_list_boot_cids_empty(self):
        """Test listing boot CIDs when none exist (only non-boot CIDs)."""
        with self.app.app_context():
            # Create a non-boot CID
            content = b"just text, not json"
            cid_value = generate_cid(content)
            create_cid_record(cid_value, content, self.user_id)

            boot_cids = list_boot_cids()
            # Should not include the text CID
            # (may include boot CIDs from cids directory though)
            text_cid_found = any(cid == cid_value for cid, _ in boot_cids)
            self.assertFalse(text_cid_found)

    def test_list_boot_cids_with_valid_boot_cids(self):
        """Test listing boot CIDs returns valid boot CIDs."""
        with self.app.app_context():
            # Create valid boot CIDs
            boot1 = json.dumps({'aliases': 'AAAAAAAA'}).encode('utf-8')
            cid1 = generate_cid(boot1)
            create_cid_record(cid1, boot1, self.user_id)

            boot2 = json.dumps({'servers': 'AAAAAAAB', 'variables': 'AAAAAAAC'}).encode('utf-8')
            cid2 = generate_cid(boot2)
            create_cid_record(cid2, boot2, self.user_id)

            # Create a non-boot CID
            non_boot = b"not a boot cid"
            cid3 = generate_cid(non_boot)
            create_cid_record(cid3, non_boot, self.user_id)

            boot_cids = list_boot_cids()

            # Should include our boot CIDs
            cid_values = [cid for cid, _ in boot_cids]
            self.assertIn(cid1, cid_values)
            self.assertIn(cid2, cid_values)
            self.assertNotIn(cid3, cid_values)

    def test_list_boot_cids_metadata(self):
        """Test that metadata is correctly populated."""
        with self.app.app_context():
            boot_content = json.dumps({
                'aliases': 'AAAAAAAA',
                'servers': 'AAAAAAAB',
            }).encode('utf-8')
            cid_value = generate_cid(boot_content)
            create_cid_record(cid_value, boot_content, self.user_id)

            boot_cids = list_boot_cids()

            # Find our CID
            our_cid = None
            for cid, metadata in boot_cids:
                if cid == cid_value:
                    our_cid = (cid, metadata)
                    break

            self.assertIsNotNone(our_cid)
            _, metadata = our_cid

            # Check metadata
            self.assertEqual(metadata['size'], len(boot_content))
            self.assertEqual(metadata['uploaded_by'], self.user_id)
            self.assertIn('aliases', metadata['sections'])
            self.assertIn('servers', metadata['sections'])
            self.assertIsNotNone(metadata['created_at'])


class TestMakeHttpGetRequest(unittest.TestCase):
    """Tests for making HTTP GET requests."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        with self.app.app_context():
            db.create_all()
            self.user_id = 'test-user-123'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_make_http_get_request_valid_path(self):
        """Test making GET request to valid path."""
        with self.app.app_context():
            success, response_text, status_code = make_http_get_request(self.app, '/')
            self.assertTrue(success)
            self.assertEqual(status_code, 200)
            self.assertIsNotNone(response_text)

    def test_make_http_get_request_not_found(self):
        """Test making GET request to non-existent path."""
        with self.app.app_context():
            success, response_text, status_code = make_http_get_request(
                self.app, '/nonexistent-path-12345'
            )
            self.assertTrue(success)
            self.assertEqual(status_code, 404)
            self.assertIsNotNone(response_text)

    def test_make_http_get_request_full_url(self):
        """Test making GET request with full URL."""
        with self.app.app_context():
            success, response_text, status_code = make_http_get_request(
                self.app, 'http://localhost:5001/'
            )
            self.assertTrue(success)
            self.assertEqual(status_code, 200)
            self.assertIsNotNone(response_text)

    def test_make_http_get_request_with_query_params(self):
        """Test making GET request with query parameters."""
        with self.app.app_context():
            success, response_text, status_code = make_http_get_request(
                self.app, '/?test=value'
            )
            self.assertTrue(success)
            self.assertEqual(status_code, 200)
            self.assertIsNotNone(response_text)

    def test_make_http_get_request_cid_content(self):
        """Test making GET request to CID path."""
        with self.app.app_context():
            content = b"test content for http request"
            cid_value = generate_cid(content)
            create_cid_record(cid_value, content, self.user_id)

            success, response_text, status_code = make_http_get_request(
                self.app, f'/{cid_value}'
            )
            self.assertTrue(success)
            self.assertEqual(status_code, 200)
            self.assertIn('test content', response_text)


class TestOpenBrowser(unittest.TestCase):
    """Tests for opening browser."""

    @patch('cli.webbrowser.open')
    def test_open_browser_success(self, mock_open):
        """Test opening browser successfully."""
        mock_open.return_value = True

        result = open_browser('http://localhost:5001')
        self.assertTrue(result)
        mock_open.assert_called_once_with('http://localhost:5001')

    @patch('cli.webbrowser.open')
    def test_open_browser_failure(self, mock_open):
        """Test opening browser with exception."""
        mock_open.side_effect = Exception("Browser not found")

        result = open_browser('http://localhost:5001')
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
