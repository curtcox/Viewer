"""Test search route highlighting functionality after refactoring."""
from __future__ import annotations

import pytest
from tests.test_support import AppTestCase


class TestSearchHighlighting(AppTestCase):
    """Tests to ensure search results use TextHighlighter correctly."""

    def test_cid_search_results_include_highlighted_names(self):
        """CID search results should include name_highlighted field with proper <mark> tags.

        This test ensures the refactoring to TextHighlighter.highlight_full() works correctly.
        Previously used _highlight_full() which would cause NameError if not migrated.
        """
        from models import CID
        from db import db

        # Create a CID with searchable content
        cid_record = CID(
            path='/test-cid-path',
            file_data=b'searchable content here',
            uploaded_by_user_id=self.test_user_id,
        )
        db.session.add(cid_record)
        db.session.commit()

        # Search for a term that appears in the CID path
        response = self.client.get(
            '/search/results',
            query_string={
                'q': 'test',
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

        # Verify name_highlighted field exists and contains highlighting
        cid_item = cids['items'][0]
        self.assertIn('name_highlighted', cid_item, "CID result should have name_highlighted field")

        name_highlighted = cid_item['name_highlighted']
        self.assertIsInstance(name_highlighted, str, "name_highlighted should be a string")
        self.assertIn('<mark>', name_highlighted, "name_highlighted should contain <mark> tags for matches")
        self.assertIn('</mark>', name_highlighted, "name_highlighted should contain closing </mark> tags")

    def test_all_search_categories_include_highlighted_names(self):
        """All search result categories should include name_highlighted field.

        Ensures TextHighlighter is used consistently across all result types.
        """
        from models import Alias, Server, Variable, Secret, CID
        from db import db

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
            uploaded_by_user_id=self.test_user_id,
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
        from models import CID
        from db import db

        # Create CID with special characters
        cid_record = CID(
            path='/test<script>alert("xss")</script>',
            file_data=b'content',
            uploaded_by_user_id=self.test_user_id,
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
        self.assertIn('&quot;', name_highlighted, "Should escape quotes")
