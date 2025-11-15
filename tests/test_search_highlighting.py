#!/usr/bin/env python3
"""Test search route highlighting functionality after refactoring."""
from __future__ import annotations

import os
import unittest

# Set up test environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import create_app
from database import db
from models import Alias, CID, Secret, Server, Variable


class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and teardown."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()
        self.test_user_id = 'test_user_123'

    def tearDown(self):
        """Clean up after test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, user_id=None):
        """Helper to simulate user login."""
        if user_id is None:
            user_id = self.test_user_id

        with self.client.session_transaction() as sess:
            sess['_user_id'] = user_id
            sess['_fresh'] = True


class TestSearchHighlighting(BaseTestCase):
    """Tests to ensure search results use TextHighlighter correctly."""

    def test_cid_search_results_include_highlighted_names(self):
        """CID search results should include name_highlighted field with proper <mark> tags.

        This test ensures the refactoring to TextHighlighter.highlight_full() works correctly.
        Previously used _highlight_full() which would cause NameError if not migrated.
        """
        self.login_user()

        # Create a CID with searchable content
        # The content contains "searchable" which we'll search for
        cid_record = CID(
            path='/test-cid-path',
            file_data=b'searchable content here',
        )
        db.session.add(cid_record)
        db.session.commit()

        # Search for a term that appears in the CID content (not path)
        # This will match the file_data content
        response = self.client.get(
            '/search/results',
            query_string={
                'q': 'searchable',
                'aliases': '0',
                'servers': '0',
                'variables': '0',
                'secrets': '0',
                'cids': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # Verify CID results exist
        cids = payload['categories']['cids']
        self.assertGreater(cids['count'], 0, "Should find at least one CID result")
        self.assertGreater(len(cids['items']), 0, "CID items should not be empty")

        # Verify name_highlighted field exists
        cid_item = cids['items'][0]
        self.assertIn(
            'name_highlighted',
            cid_item,
            "CID result should have name_highlighted field"
        )

        name_highlighted = cid_item['name_highlighted']
        self.assertIsInstance(
            name_highlighted,
            str,
            "name_highlighted should be a string"
        )

        # The content matched, so we should have details with highlighting
        # The name itself (CID hash) may not contain the search term,
        # but the field should exist and be properly formatted
        self.assertTrue(
            len(name_highlighted) > 0,
            "name_highlighted should not be empty"
        )

        # Verify details contains highlighted content snippet
        details = cid_item.get('details', [])
        self.assertTrue(len(details) > 0, "Should have content details")

        # Check that content snippet has highlighting
        content_detail = details[0]
        self.assertEqual(content_detail['label'], 'Content')
        self.assertIn(
            '<mark>',
            content_detail['value'],
            "Content snippet should contain <mark> tags"
        )

    def test_cid_name_highlighting_when_search_term_in_path(self):
        """CID name should be highlighted when search term appears in the path."""
        self.login_user()

        # Create a CID where the path contains our search term
        cid_record = CID(
            path='/needle-in-path',
            file_data=b'some content',
        )
        db.session.add(cid_record)
        db.session.commit()

        # Search for term that appears in the path
        response = self.client.get(
            '/search/results',
            query_string={
                'q': 'needle',
                'aliases': '0',
                'servers': '0',
                'variables': '0',
                'secrets': '0',
                'cids': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        cids = payload['categories']['cids']
        self.assertGreater(cids['count'], 0, "Should find CID with 'needle' in path")

        cid_item = cids['items'][0]
        name_highlighted = cid_item.get('name_highlighted', '')

        # Verify name_highlighted exists and is a string
        self.assertIsInstance(name_highlighted, str)
        self.assertTrue(len(name_highlighted) > 0, "name_highlighted should not be empty")

        # Verify the search term is actually highlighted with <mark> tags
        self.assertIn(
            '<mark>',
            name_highlighted,
            "name_highlighted should contain <mark> tags when search term matches"
        )

        # Verify the search term appears within <mark> tags
        # Check for case-insensitive match since query is lowercased
        import re
        mark_pattern = re.compile(r'<mark>([^<]*)</mark>', re.IGNORECASE)
        marked_text = mark_pattern.findall(name_highlighted)
        self.assertTrue(
            any('needle' in text.lower() for text in marked_text),
            f"Search term 'needle' should appear within <mark> tags in: {name_highlighted}"
        )

    def test_all_search_categories_include_highlighted_names(self):
        """All search result categories should include name_highlighted field.

        Ensures TextHighlighter is used consistently across all result types.
        """
        self.login_user()

        # Create test data for all categories
        alias = Alias(
            name='query-alias',
            definition='literal /servers/test-server',
            user_id=self.test_user_id,
        )
        server = Server(
            name='query-server',
            definition='def main(): return "query"',
            user_id=self.test_user_id,
        )
        variable = Variable(
            name='query-var',
            definition='query value',
            user_id=self.test_user_id,
        )
        secret = Secret(
            name='query-secret',
            definition='query token',
            user_id=self.test_user_id,
        )
        cid_record = CID(
            path='/query-cid',
            file_data=b'query content',
        )

        db.session.add_all([alias, server, variable, secret, cid_record])
        db.session.commit()

        # Search for 'query' which appears in all items
        response = self.client.get('/search/results', query_string={'q': 'query'})
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        categories = payload['categories']

        # Check each category has name_highlighted with proper highlighting
        for category_name in ['aliases', 'servers', 'variables', 'secrets', 'cids']:
            category = categories[category_name]

            if category['count'] > 0:
                item = category['items'][0]
                self.assertIn(
                    'name_highlighted',
                    item,
                    f"{category_name} result should have name_highlighted field"
                )

                name_highlighted = item['name_highlighted']
                self.assertIn(
                    '<mark>',
                    name_highlighted,
                    f"{category_name} name_highlighted should contain <mark> tags"
                )

    def test_search_highlighting_handles_special_characters(self):
        """Search highlighting should properly escape special characters.

        Ensures TextHighlighter.highlight_full() uses proper escaping.
        """
        self.login_user()

        # Create CID with special characters
        cid_record = CID(
            path='/test<script>alert("xss")</script>',
            file_data=b'content',
        )
        db.session.add(cid_record)
        db.session.commit()

        response = self.client.get(
            '/search/results',
            query_string={'q': 'test', 'cids': '1'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        cid_item = payload['categories']['cids']['items'][0]
        name_highlighted = cid_item['name_highlighted']

        # Should escape HTML but keep <mark> tags
        self.assertIn('<mark>', name_highlighted)
        self.assertIn('&lt;script&gt;', name_highlighted, "Should escape < and >")
        # Quotes can be escaped as &quot; or &#34; (both valid HTML entities)
        self.assertTrue(
            '&quot;' in name_highlighted or '&#34;' in name_highlighted,
            "Should escape quotes"
        )
