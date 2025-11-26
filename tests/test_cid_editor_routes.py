"""Unit tests for CID editor routes."""

import unittest

from cid_core import generate_cid, DIRECT_CONTENT_EMBED_LIMIT


class TestCidEditorRoutes(unittest.TestCase):
    """Tests for CID editor API routes."""

    def setUp(self):
        """Set up test client."""
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def test_check_cid_empty_content(self):
        """Test checking empty content returns not_a_cid status."""
        response = self.client.post(
            '/api/cid/check',
            json={'content': ''},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['is_cid'])
        self.assertEqual(data['status'], 'not_a_cid')

    def test_check_cid_regular_text(self):
        """Test checking regular text returns not_a_cid status."""
        response = self.client.post(
            '/api/cid/check',
            json={'content': 'Hello, World!'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['is_cid'])
        self.assertEqual(data['status'], 'not_a_cid')

    def test_check_cid_embedded_content(self):
        """Test checking CID with embedded content."""
        cid = generate_cid(b"test content")
        response = self.client.post(
            '/api/cid/check',
            json={'content': cid},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['is_cid'])
        self.assertEqual(data['status'], 'content_embedded')
        self.assertTrue(data['has_content'])
        self.assertEqual(data['content'], 'test content')
        self.assertIn('cid_link_html', data)

    def test_check_cid_not_found(self):
        """Test checking CID with content not in database."""
        # Create a CID for content larger than embed limit
        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1)
        cid = generate_cid(content)
        response = self.client.post(
            '/api/cid/check',
            json={'content': cid},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['is_cid'])
        self.assertEqual(data['status'], 'content_not_found')
        self.assertFalse(data['has_content'])

    def test_generate_cid_empty_content(self):
        """Test generating CID for empty content."""
        response = self.client.post(
            '/api/cid/generate',
            json={'content': '', 'store': False},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['cid_value'], 'AAAAAAAA')
        self.assertIn('cid_link_html', data)

    def test_generate_cid_text_content(self):
        """Test generating CID for text content."""
        response = self.client.post(
            '/api/cid/generate',
            json={'content': 'Hello', 'store': False},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(len(data['cid_value']) >= 8)
        self.assertIn('cid_link_html', data)

    def test_generate_cid_store(self):
        """Test generating and storing CID."""
        response = self.client.post(
            '/api/cid/generate',
            json={'content': 'Store this content', 'store': True},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(len(data['cid_value']) >= 8)

    def test_check_cid_no_json_body(self):
        """Test checking CID with no JSON body."""
        response = self.client.post('/api/cid/check')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['is_cid'])

    def test_generate_cid_no_json_body(self):
        """Test generating CID with no JSON body."""
        response = self.client.post('/api/cid/generate')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['cid_value'], 'AAAAAAAA')


if __name__ == "__main__":
    unittest.main()
