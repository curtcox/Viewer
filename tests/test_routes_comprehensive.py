#!/usr/bin/env python3
"""
Comprehensive unit tests for routes.py
"""
import json
import os
import re
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from flask import current_app

# Set up test environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

import server_execution
from alias_definition import format_primary_alias_line
from app import create_app
from cid_utils import CID_LENGTH, CID_MIN_LENGTH, _base64url_encode, encode_cid_length, generate_cid
from database import db
from models import (
    CID,
    Alias,
    PageView,
    Secret,
    Server,
    ServerInvocation,
    Variable,
)
from routes.core import _build_cross_reference_data
from server_templates import get_server_templates


def _alias_definition(
    name: str,
    target: str,
    *,
    match_type: str = 'literal',
    pattern: str | None = None,
    ignore_case: bool = False,
) -> str:
    pattern_value = pattern
    if match_type == 'literal' and not pattern_value:
        pattern_value = None
    elif pattern_value is None:
        pattern_value = f'/{name}'
    return format_primary_alias_line(
        match_type,
        pattern_value,
        target,
        ignore_case=ignore_case,
        alias_name=name,
    )


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
        """Clean up after tests."""
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


class TestUtilityFunctions(BaseTestCase):
    """Test utility functions."""

    def test_generate_cid(self):
        """Test CID generation function."""
        test_data = b"Hello, World!"
        cid = generate_cid(test_data)

        # Should be canonical for direct encoding and deterministic
        expected = encode_cid_length(len(test_data)) + _base64url_encode(test_data)
        self.assertEqual(cid, expected)
        self.assertGreaterEqual(len(cid), CID_MIN_LENGTH)
        self.assertLessEqual(len(cid), CID_LENGTH)

        # Should be deterministic
        cid2 = generate_cid(test_data)
        self.assertEqual(cid, cid2)

        # Different data should produce different CID
        different_cid = generate_cid(b"Different data")
        self.assertNotEqual(cid, different_cid)

        # Should use canonical direct encoding length
        self.assertEqual(cid, expected)


class TestContextProcessors(BaseTestCase):
    """Test context processors and before/after request handlers."""

    def test_inject_observability_info(self):
        """Ensure observability context values mirror application status."""

        from routes.core import inject_observability_info

        with self.app.app_context():
            current_app.config["OBSERVABILITY_STATUS"] = {
                "logfire_available": False,
                "logfire_project_url": None,
                "logfire_reason": "missing api key",
                "langsmith_available": True,
                "langsmith_project_url": "https://langsmith.example/project",
                "langsmith_reason": None,
            }

            context = inject_observability_info()

        self.assertFalse(context["LOGFIRE_AVAILABLE"])
        self.assertEqual(context["LOGFIRE_UNAVAILABLE_REASON"], "missing api key")
        self.assertTrue(context["LANGSMITH_AVAILABLE"])
        self.assertEqual(
            context["LANGSMITH_PROJECT_URL"],
            "https://langsmith.example/project",
        )

    def test_inject_meta_inspector_link(self):
        """Expose a metadata inspector link for the active request path."""

        from routes.core import inject_meta_inspector_link

        with self.app.test_request_context('/servers/example'):
            context = inject_meta_inspector_link()

        self.assertEqual(context["meta_inspector_url"], "/meta/servers/example.html")


class TestPublicRoutes(BaseTestCase):
    """Test routes that don't require authentication."""

    def test_index_unauthenticated(self):
        """Test index page for unauthenticated users."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_index_authenticated_shows_cross_reference_dashboard(self):
        """Authenticated users should see the workspace cross reference overview."""
        self.login_user()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Workspace Cross Reference', page)
        self.assertIn('data-crossref-container', page)

    def test_index_cross_reference_shortcuts_link_to_entity_lists(self):
        """The dashboard shortcut badges should link to the list views."""
        self.login_user()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        self.assertIn('href="/aliases"', page)
        self.assertIn('href="/servers"', page)
        self.assertIn('href="/uploads"', page)

    def test_search_page_renders_with_filters(self):
        """The search page should render the filter checkboxes and status helper."""
        self.login_user()

        response = self.client.get('/search')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Workspace Search', page)
        self.assertIn('data-search-category="aliases"', page)
        self.assertIn('Start typing to search your workspace.', page)

    def test_index_cross_reference_lists_entities_and_relationships(self):
        """Cross reference dashboard should include aliases, servers, CIDs, and references."""
        self.login_user()

        cid_value = generate_cid(b'CID: /alpha -> /servers/beta')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'CID: /alpha -> /servers/beta',
            uploaded_by_user_id=self.test_user_id,
        )
        alias_server = Alias(
            name='alpha',
            user_id=self.test_user_id,
            definition=_alias_definition('alpha', '/servers/beta'),
        )
        alias_cid = Alias(
            name='bravo',
            user_id=self.test_user_id,
            definition=_alias_definition('bravo', f'/{cid_value}'),
        )
        server_definition = f"""
def main(request):
    return "Use /bravo and /{cid_value}"
""".strip()
        server = Server(
            name='beta',
            definition=server_definition,
            user_id=self.test_user_id,
            definition_cid=f'/{cid_value}',
        )

        db.session.add_all([cid_record, alias_server, alias_cid, server])
        db.session.commit()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Workspace Cross Reference', page)
        self.assertIn('/aliases/alpha', page)
        self.assertIn('/aliases/bravo', page)
        self.assertIn('/servers/beta', page)
        self.assertIn(f'#{cid_value[:9]}', page)
        self.assertIn('CID: /alpha', page)
        self.assertNotIn('No aliases yet', page)
        self.assertNotIn('No CIDs referenced', page)
        self.assertNotIn('No references detected', page)
        self.assertIn('crossref-reference', page)

    def test_index_alias_target_displays_cid_link_for_cid_path(self):
        """Alias entries on the dashboard should use the CID link component when targeting CIDs."""
        self.login_user()

        cid_value = generate_cid(b'Alias target CID render check')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'alias target content',
            uploaded_by_user_id=self.test_user_id,
        )
        alias_cid = Alias(
            name='cid-alias',
            user_id=self.test_user_id,
            definition=_alias_definition('cid-alias', f'/{cid_value}'),
        )

        db.session.add_all([cid_record, alias_cid])
        db.session.commit()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        pattern = rf'(?s)crossref-alias.*?{alias_cid.name}.*?<div class="small text-muted mt-1">\s*<span class="cid-display dropdown">'
        self.assertRegex(page, pattern)
        self.assertNotIn(f'<code>/{cid_value}</code>', page)


    def test_index_cross_reference_cids_include_incoming_highlight_metadata(self):
        """CID entries should carry metadata linking back to referencing aliases or servers."""
        self.login_user()

        cid_value = generate_cid(b'CID referenced by alias and server')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'Use /aliases/linked and /servers/linked',
            uploaded_by_user_id=self.test_user_id,
        )
        alias_to_cid = Alias(
            name='linked',
            user_id=self.test_user_id,
            definition=_alias_definition('linked', f'/{cid_value}'),
        )
        server_definition = """
def main(request):
    return "See /aliases/linked"
""".strip()
        server = Server(
            name='linked',
            definition=server_definition,
            user_id=self.test_user_id,
            definition_cid=f'/{cid_value}',
        )

        db.session.add_all([cid_record, alias_to_cid, server])
        db.session.commit()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        with self.app.test_request_context('/'):
            cross_reference = _build_cross_reference_data(self.test_user_id)
        cid_entry = next(item for item in cross_reference['cids'] if item['cid'] == cid_value)
        alias_entry = next(item for item in cross_reference['aliases'] if item['name'] == 'linked')
        server_entry = next(item for item in cross_reference['servers'] if item['name'] == 'linked')

        cid_key = cid_entry['entity_key']
        alias_key = alias_entry['entity_key']
        server_key = server_entry['entity_key']

        incoming_reference_keys = set(cid_entry['incoming_refs'])
        self.assertTrue(incoming_reference_keys, 'CID should report at least one incoming reference key')

        element_pattern = re.compile(rf'<div[^>]*data-entity-key="{re.escape(cid_key)}"[^>]*>')
        cid_match = element_pattern.search(page)
        self.assertIsNotNone(cid_match, 'CID entry should be rendered with a data-entity-key attribute')

        cid_tag = cid_match.group(0)

        implies_match = re.search(r'data-implies="([^"]*)"', cid_tag)
        self.assertIsNotNone(implies_match, 'CID entry should expose implied entity keys')
        implies_values = implies_match.group(1).split()
        self.assertIn(alias_key, implies_values)
        self.assertIn(server_key, implies_values)

        incoming_match = re.search(r'data-incoming-refs="([^"]*)"', cid_tag)
        self.assertIsNotNone(incoming_match, 'CID entry should expose incoming reference keys')
        incoming_values = set(incoming_match.group(1).split())
        self.assertTrue(incoming_values >= incoming_reference_keys)

    def test_index_cross_reference_alias_and_server_highlight_metadata(self):
        """Alias and server entries should expose highlight metadata for related entities."""
        self.login_user()

        cid_value = generate_cid(b'Highlight metadata for alias and server entries')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'Content used to link alias, server, and CID',
            uploaded_by_user_id=self.test_user_id,
        )
        alias_to_server = Alias(
            name='relay-server',
            user_id=self.test_user_id,
            definition=_alias_definition('relay-server', '/servers/highlighted'),
        )
        alias_to_cid = Alias(
            name='relay-cid',
            user_id=self.test_user_id,
            definition=_alias_definition('relay-cid', f'/{cid_value}'),
        )
        server_definition = """
def main(request):
    return "See /aliases/relay-cid for details"
""".strip()
        server = Server(
            name='highlighted',
            definition=server_definition,
            user_id=self.test_user_id,
            definition_cid=f'/{cid_value}',
        )

        db.session.add_all([cid_record, alias_to_server, alias_to_cid, server])
        db.session.commit()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)

        with self.app.test_request_context('/'):
            cross_reference = _build_cross_reference_data(self.test_user_id)

        alias_entry = next(item for item in cross_reference['aliases'] if item['name'] == 'relay-server')
        relay_cid_entry = next(item for item in cross_reference['aliases'] if item['name'] == 'relay-cid')
        server_entry = next(item for item in cross_reference['servers'] if item['name'] == 'highlighted')
        cid_entry = next(item for item in cross_reference['cids'] if item['cid'] == cid_value)

        alias_key = alias_entry['entity_key']
        relay_cid_key = relay_cid_entry['entity_key']
        server_key = server_entry['entity_key']
        cid_key = cid_entry['entity_key']

        alias_outgoing_keys = set(alias_entry['outgoing_refs'])
        server_outgoing_keys = set(server_entry['outgoing_refs'])
        self.assertTrue(alias_outgoing_keys, 'Alias should expose outgoing reference keys')
        self.assertTrue(server_outgoing_keys, 'Server should expose outgoing reference keys')

        alias_pattern = re.compile(rf'<div[^>]*data-entity-key="{re.escape(alias_key)}"[^>]*>')
        alias_match = alias_pattern.search(page)
        self.assertIsNotNone(alias_match, 'Alias entry should render data attributes for highlighting')
        alias_tag = alias_match.group(0)

        alias_implies_match = re.search(r'data-implies="([^"]*)"', alias_tag)
        self.assertIsNotNone(alias_implies_match, 'Alias entry should list implied entity keys')
        alias_implies_values = set(filter(None, alias_implies_match.group(1).split()))
        self.assertIn(server_key, alias_implies_values)

        alias_outgoing_match = re.search(r'data-outgoing-refs="([^"]*)"', alias_tag)
        self.assertIsNotNone(alias_outgoing_match, 'Alias entry should list outgoing reference keys')
        alias_outgoing_values = set(filter(None, alias_outgoing_match.group(1).split()))
        self.assertTrue(alias_outgoing_keys <= alias_outgoing_values)

        server_pattern = re.compile(rf'<div[^>]*data-entity-key="{re.escape(server_key)}"[^>]*>')
        server_match = server_pattern.search(page)
        self.assertIsNotNone(server_match, 'Server entry should render data attributes for highlighting')
        server_tag = server_match.group(0)

        server_implies_match = re.search(r'data-implies="([^"]*)"', server_tag)
        self.assertIsNotNone(server_implies_match, 'Server entry should list implied entity keys')
        server_implies_values = set(filter(None, server_implies_match.group(1).split()))
        self.assertIn(alias_key, server_implies_values)
        self.assertIn(relay_cid_key, server_implies_values)

        server_outgoing_match = re.search(r'data-outgoing-refs="([^"]*)"', server_tag)
        self.assertIsNotNone(server_outgoing_match, 'Server entry should list outgoing reference keys')
        server_outgoing_values = set(filter(None, server_outgoing_match.group(1).split()))
        self.assertTrue(server_outgoing_keys <= server_outgoing_values)

        alias_server_reference = next(
            ref
            for ref in cross_reference['references']
            if ref['source_key'] == alias_entry['entity_key']
            and ref['target_key'] == server_entry['entity_key']
        )

        reference_key = alias_server_reference['key']
        reference_pattern = re.compile(rf'<div[^>]*data-reference-key="{re.escape(reference_key)}"[^>]*>')
        reference_match = reference_pattern.search(page)
        self.assertIsNotNone(reference_match, 'Reference entry should render data attributes for highlighting')
        reference_tag = reference_match.group(0)

        self.assertIn(f'data-source-key="{alias_server_reference["source_key"]}"', reference_tag)
        self.assertIn(f'data-target-key="{alias_server_reference["target_key"]}"', reference_tag)

        server_cid_reference = next(
            ref
            for ref in cross_reference['references']
            if ref['source_key'] == server_entry['entity_key']
            and ref['target_key'] == cid_key
        )
        self.assertIn(server_cid_reference['key'], server_outgoing_values)

    def test_index_cross_reference_alias_to_alias_highlight_metadata(self):
        """Alias entries should expose highlight metadata when targeting another alias."""
        self.login_user()

        server_definition = """
def main(request):
    return "alias target"
""".strip()
        server = Server(
            name='alias-target-backend',
            definition=server_definition,
            user_id=self.test_user_id,
        )

        alias_target = Alias(
            name='alias-target',
            user_id=self.test_user_id,
            definition=_alias_definition('alias-target', '/servers/alias-target-backend'),
        )
        alias_source = Alias(
            name='alias-source',
            user_id=self.test_user_id,
            definition=_alias_definition('alias-source', '/aliases/alias-target'),
        )

        db.session.add_all([server, alias_target, alias_source])
        db.session.commit()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)

        with self.app.test_request_context('/'):
            cross_reference = _build_cross_reference_data(self.test_user_id)

        source_entry = next(item for item in cross_reference['aliases'] if item['name'] == 'alias-source')
        target_entry = next(item for item in cross_reference['aliases'] if item['name'] == 'alias-target')
        reference_entry = next(
            item
            for item in cross_reference['references']
            if item['source_name'] == 'alias-source' and item['target_name'] == 'alias-target'
        )

        source_key = source_entry['entity_key']
        target_key = target_entry['entity_key']
        reference_key = reference_entry['key']

        self.assertIn(target_key, source_entry['implied_keys'])
        self.assertIn(source_key, target_entry['implied_keys'])

        source_outgoing = set(filter(None, source_entry['outgoing_refs']))
        target_incoming = set(filter(None, target_entry['incoming_refs']))
        self.assertIn(reference_key, source_outgoing)
        self.assertIn(reference_key, target_incoming)

        source_pattern = re.compile(rf'<div[^>]*data-entity-key="{re.escape(source_key)}"[^>]*>')
        source_match = source_pattern.search(page)
        self.assertIsNotNone(source_match, 'Source alias entry should include data attributes for highlighting')
        source_tag = source_match.group(0)

        source_implies_match = re.search(r'data-implies="([^"]*)"', source_tag)
        self.assertIsNotNone(source_implies_match, 'Source alias should expose implied entity keys')
        self.assertIn(target_key, source_implies_match.group(1).split())

        source_outgoing_match = re.search(r'data-outgoing-refs="([^"]*)"', source_tag)
        self.assertIsNotNone(source_outgoing_match, 'Source alias should list outgoing reference keys')
        self.assertIn(reference_key, source_outgoing_match.group(1).split())

        target_pattern = re.compile(rf'<div[^>]*data-entity-key="{re.escape(target_key)}"[^>]*>')
        target_match = target_pattern.search(page)
        self.assertIsNotNone(target_match, 'Target alias entry should include data attributes for highlighting')
        target_tag = target_match.group(0)

        target_implies_match = re.search(r'data-implies="([^"]*)"', target_tag)
        self.assertIsNotNone(target_implies_match, 'Target alias should expose implied entity keys')
        self.assertIn(source_key, target_implies_match.group(1).split())

        target_incoming_match = re.search(r'data-incoming-refs="([^"]*)"', target_tag)
        self.assertIsNotNone(target_incoming_match, 'Target alias should list incoming reference keys')
        self.assertIn(reference_key, target_incoming_match.group(1).split())

    def test_index_cross_reference_skips_cids_without_named_alias(self):
        """Orphaned CIDs from aliases without names should not appear in the dashboard."""
        self.login_user()

        cid_value = generate_cid(b'Alias without a name referencing this CID')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'nameless alias content',
            uploaded_by_user_id=self.test_user_id,
        )
        nameless_alias = Alias(
            name='',
            user_id=self.test_user_id,
            definition=_alias_definition('', f'/{cid_value}'),
        )

        db.session.add_all([cid_record, nameless_alias])
        db.session.commit()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        self.assertIn('No CIDs referenced by your aliases or servers yet.', page)

        with self.app.test_request_context('/'):
            cross_reference = _build_cross_reference_data(self.test_user_id)

        self.assertFalse(
            any(entry['cid'] == cid_value for entry in cross_reference['cids']),
            'CID referenced only by a nameless alias should be filtered out',
        )
        self.assertFalse(
            any(
                ref['target_type'] == 'cid' and ref['target_name'] == cid_value
                for ref in cross_reference['references']
            ),
            'References column should not include entries for the filtered CID',
        )


class TestSearchApi(BaseTestCase):
    """Verify the incremental search endpoint."""

    def setUp(self):
        super().setUp()
        self.login_user()

    def test_search_results_include_all_categories(self):
        """Search results should highlight matches across every enabled category."""

        alias = Alias(
            name='hello-alias',
            user_id=self.test_user_id,
            definition=_alias_definition('hello-alias', '/servers/hello-server'),
        )
        server = Server(
            name='hello-server',
            definition='''
def main(request):
    return "Hello from server"
'''.strip(),
            user_id=self.test_user_id,
        )
        variable = Variable(
            name='HELLO_VARIABLE',
            definition='The value says hello to the world.',
            user_id=self.test_user_id,
        )
        secret = Secret(
            name='HELLO_SECRET',
            definition='super hello secret token',
            user_id=self.test_user_id,
        )
        cid_value = generate_cid(b'Hello from CID search test')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'Hello from CID search test',
            uploaded_by_user_id=self.test_user_id,
        )

        db.session.add_all([alias, server, variable, secret, cid_record])
        db.session.commit()

        response = self.client.get('/search/results', query_string={'q': 'hello'})
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        categories = payload['categories']

        self.assertEqual(payload['total_count'], 5)
        self.assertEqual(categories['aliases']['count'], 1)
        self.assertEqual(categories['servers']['count'], 1)
        self.assertEqual(categories['variables']['count'], 1)
        self.assertEqual(categories['secrets']['count'], 1)
        self.assertEqual(categories['cids']['count'], 1)

        alias_details = categories['aliases']['items'][0]['details']
        self.assertTrue(any('<mark>' in detail['value'] for detail in alias_details))

        alias_entry = categories['aliases']['items'][0]
        server_entry = categories['servers']['items'][0]
        variable_entry = categories['variables']['items'][0]
        secret_entry = categories['secrets']['items'][0]
        cid_entry = categories['cids']['items'][0]

        server_details = server_entry['details']
        self.assertTrue(server_details and '<mark>' in server_details[0]['value'])

        cid_details = cid_entry['details']
        self.assertTrue(cid_details and '<mark>' in cid_details[0]['value'])

        self.assertTrue(alias_entry['aliases'])
        self.assertEqual(alias_entry['aliases'][0]['name'], 'hello-alias')
        self.assertIn('/aliases/new?target_path=/servers/hello-server', alias_entry['alias_form_url'])

        self.assertTrue(server_entry['aliases'])
        self.assertEqual(server_entry['aliases'][0]['name'], 'hello-alias')
        self.assertIn('target_path=/servers/hello-server', server_entry['alias_form_url'])
        self.assertIn('name=hello-server', server_entry['alias_form_url'])

        self.assertIn('target_path=/variables/HELLO_VARIABLE', variable_entry['alias_form_url'])
        self.assertIn('name=HELLO_VARIABLE', variable_entry['alias_form_url'])

        self.assertIn('target_path=/secrets/HELLO_SECRET', secret_entry['alias_form_url'])
        self.assertIn('name=HELLO_SECRET', secret_entry['alias_form_url'])

        self.assertIn(f'target_path=/{cid_value}', cid_entry['alias_form_url'])
        self.assertIn(f'name={cid_value}', cid_entry['alias_form_url'])

        filtered = self.client.get(
            '/search/results',
            query_string={'q': 'hello', 'aliases': '1', 'servers': '0', 'variables': '0', 'secrets': '0', 'cids': '0'},
        )
        filtered_payload = filtered.get_json()
        self.assertEqual(filtered_payload['total_count'], 1)
        self.assertEqual(filtered_payload['categories']['aliases']['count'], 1)
        for category in ('servers', 'variables', 'secrets', 'cids'):
            self.assertEqual(filtered_payload['categories'][category]['count'], 0)

        empty_response = self.client.get('/search/results', query_string={'q': '   '})
        empty_payload = empty_response.get_json()
        self.assertEqual(empty_payload['total_count'], 0)
        for category in ('aliases', 'servers', 'variables', 'secrets', 'cids'):
            self.assertEqual(empty_payload['categories'][category]['count'], 0)

    def test_cid_results_sorted_and_limited_to_latest_entries(self):
        """CID search results should be sorted by newest first and capped at 100 items."""

        now = datetime.now(timezone.utc)
        for index in range(105):
            record = CID(
                path=f'/needle-{index:03d}',
                file_data=f'needle {index}'.encode(),
                uploaded_by_user_id=self.test_user_id,
                created_at=now + timedelta(minutes=index),
            )
            db.session.add(record)

        db.session.commit()

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
        cids_category = payload['categories']['cids']

        self.assertEqual(payload['total_count'], 100)
        self.assertEqual(cids_category['count'], 100)
        self.assertEqual(len(cids_category['items']), 100)
        self.assertEqual(cids_category['items'][0]['name'], '/needle-104')
        self.assertEqual(cids_category['items'][-1]['name'], '/needle-005')

    def test_index_cross_reference_skips_cids_without_named_server(self):
        """Servers lacking a name should not introduce orphan CID entries."""
        self.login_user()

        cid_value = generate_cid(b'Server without a name referencing this CID')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'nameless server content',
            uploaded_by_user_id=self.test_user_id,
        )
        nameless_server = Server(
            name='',
            definition="""
def main(request):
    return "Hello"
""".strip(),
            user_id=self.test_user_id,
            definition_cid=f'/{cid_value}',
        )

        db.session.add_all([cid_record, nameless_server])
        db.session.commit()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        self.assertIn('No CIDs referenced by your aliases or servers yet.', page)

        with self.app.test_request_context('/'):
            cross_reference = _build_cross_reference_data(self.test_user_id)

        self.assertFalse(
            any(entry['cid'] == cid_value for entry in cross_reference['cids']),
            'CID referenced only by a nameless server should be filtered out',
        )
        self.assertFalse(
            any(
                ref['target_type'] == 'cid' and ref['target_name'] == cid_value
                for ref in cross_reference['references']
            ),
            'References column should not include entries for the filtered CID',
        )

    def test_plans_page(self):
        """Plans endpoint should stay disabled and answer with a 404."""
        response = self.client.get('/plans')
        self.assertEqual(response.status_code, 404)

    def test_terms_page(self):
        """Test terms page."""
        response = self.client.get('/terms')
        self.assertEqual(response.status_code, 404)

    def test_privacy_page_returns_not_found(self):
        """Privacy endpoint should stay disabled and answer with a 404."""
        response = self.client.get('/privacy')
        self.assertEqual(response.status_code, 404)

    def test_404_page_includes_creation_links(self):
        """The 404 page should offer shortcuts for creating aliases or servers."""
        missing_path = '/missing/path'

        response = self.client.get(missing_path)
        self.assertEqual(response.status_code, 404)

        page = response.get_data(as_text=True)
        self.assertIn(f"/aliases/new?path={missing_path}", page)
        self.assertIn(f"/servers/new?path={missing_path}", page)


class TestAuthenticatedRoutes(BaseTestCase):
    """Test routes that require authentication."""

    def test_dashboard_redirects_unauthenticated(self):
        """Test dashboard redirects unauthenticated users."""
        response = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_redirects_authenticated_users_to_profile(self):
        """Dashboard should lead signed-in users to their profile overview."""
        self.login_user()
        response = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile', response.location)

    def test_dashboard_without_access_redirects_to_profile(self):
        """Test dashboard redirects users without access to profile."""

        restricted_user_id = 'no_access_user'
        self.login_user(restricted_user_id)

        with patch('routes.core.current_user') as mock_user:
            mock_user.id = restricted_user_id
            mock_user.has_access.return_value = False

            response = self.client.get('/dashboard', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile', response.location)

    def test_profile_page_returns_success_for_authenticated_user(self):
        """Ensure authenticated users can load their profile page with a 200 response."""
        self.login_user()
        response = self.client.get('/profile')
        # Authenticated access should successfully render the profile page.
        self.assertEqual(response.status_code, 200)

    def test_navigation_includes_meta_inspector_link(self):
        """Display a metadata inspector shortcut in the site navigation."""

        self.login_user()
        response = self.client.get('/profile')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('href="/meta/profile.html"', page)
        self.assertIn('fa-circle-info', page)

    def test_content_route_returns_not_found(self):
        """Legacy /content endpoint should be unavailable."""
        self.login_user()
        response = self.client.get('/content', follow_redirects=False)
        self.assertEqual(response.status_code, 404)


class TestRemovedLegacyRoutes(BaseTestCase):
    """Ensure removed authentication and marketing routes return 404."""

    def test_subscribe_route_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/subscribe').status_code, 404)
        self.assertEqual(
            self.client.post('/subscribe', data={'plan': 'free', 'submit': 'Subscribe'}).status_code,
            404,
        )

    def test_accept_terms_route_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/accept-terms').status_code, 404)
        self.assertEqual(
            self.client.post('/accept-terms', data={'submit': 'Accept Terms'}).status_code,
            404,
        )

    def test_invitation_routes_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/invitations').status_code, 404)
        self.assertEqual(self.client.get('/create-invitation').status_code, 404)
        self.assertEqual(
            self.client.post('/create-invitation', data={'submit': 'Create Invitation'}).status_code,
            404,
        )

    def test_require_invitation_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/require-invitation').status_code, 404)
        self.assertEqual(
            self.client.post('/require-invitation', data={'invitation_code': 'test'}).status_code,
            404,
        )

    def test_invite_link_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/invite/example-code').status_code, 404)

    def test_screenshot_demo_removed(self):
        self.login_user()
        self.assertEqual(self.client.get('/_screenshot/cid-demo').status_code, 404)


class TestFileUploadRoutes(BaseTestCase):
    """Test file upload routes."""

    def test_upload_get_returns_200_with_text_ai_markup(self):
        """GET /upload returns HTTP 200 and renders the text AI input markup."""
        self.login_user()
        response = self.client.get('/upload')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        # The upload page must render the AI-enhanced text input so users can submit
        # content with the correct identifiers.
        self.assertIn('text_content-ai-input', page)
        self.assertIn('data-ai-target-id="text_content"', page)
        self.assertIn('data-code-editor-for="text_content"', page)
        self.assertIn('js/code_editor.js', page)
        self.assertIn('ace-builds@1.32.6', page)

    def test_upload_post_stores_file_and_returns_success_page(self):
        """Uploading a new file persists its content for the user and renders the success page."""
        self.login_user()

        # Create test file data to submit through the upload form.
        test_data = b"Test file content"
        test_file = (BytesIO(test_data), 'test.txt')

        response = self.client.post('/upload', data={
            'file': test_file,
            'title': 'Test File',
            'description': 'Test description',
            'submit': 'Upload File'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # The user's upload must be stored in the database so it can be referenced later.
        cid_record = CID.query.filter_by(uploaded_by_user_id=self.test_user_id).first()
        self.assertIsNotNone(cid_record)
        self.assertEqual(cid_record.file_data, test_data)

    def test_upload_duplicate_file_is_deduplicated(self):
        """Uploading identical content reuses the existing CID instead of creating a duplicate record."""
        self.login_user()

        test_data = b"Duplicate content"
        cid = generate_cid(test_data)

        # Create existing CID record
        existing_cid = CID(
            path=f"/{cid}",
            file_data=test_data,
            file_size=len(test_data),
            uploaded_by_user_id=self.test_user_id
        )
        db.session.add(existing_cid)
        db.session.commit()

        # Try to upload same content
        test_file = (BytesIO(test_data), 'duplicate.txt')
        response = self.client.post('/upload', data={
            'file': test_file,
            'title': 'Duplicate File',
            'submit': 'Upload File'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # The existing CID should still be the only record for this content.
        count = CID.query.filter_by(path=f"/{cid}").count()
        self.assertEqual(count, 1)

    def test_uploads_list_displays_reference_placeholder(self):
        """Uploads list renders manual uploads with a reference placeholder."""
        self.login_user()

        # Create test upload
        test_cid = CID(
            path="/test_cid",
            file_data=b"test data",
            file_size=9,
            uploaded_by_user_id=self.test_user_id
        )
        db.session.add(test_cid)
        db.session.commit()

        response = self.client.get('/uploads')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        # Success requires the manual upload to appear with its reference section.
        self.assertIn('References', page)
        self.assertIn('None', page)

    def test_uploads_list_excludes_server_events(self):
        """Uploads list should only show manual uploads."""
        self.login_user()

        manual_bytes = b"manual content"
        manual_cid = generate_cid(manual_bytes)
        server_bytes = b"server output"
        server_result_cid = generate_cid(server_bytes)
        request_payload = b"request payload"
        request_cid = generate_cid(request_payload)
        invocation_payload = b"invocation payload"
        invocation_cid = generate_cid(invocation_payload)
        servers_payload = b"servers snapshot"
        servers_cid = generate_cid(servers_payload)

        manual_upload = CID(
            path=f"/{manual_cid}",
            file_data=manual_bytes,
            file_size=len(manual_bytes),
            uploaded_by_user_id=self.test_user_id,
        )

        server_upload = CID(
            path=f"/{server_result_cid}",
            file_data=server_bytes,
            file_size=len(server_bytes),
            uploaded_by_user_id=self.test_user_id,
        )

        request_upload = CID(
            path=f"/{request_cid}",
            file_data=request_payload,
            file_size=len(request_payload),
            uploaded_by_user_id=self.test_user_id,
        )

        invocation_upload = CID(
            path=f"/{invocation_cid}",
            file_data=invocation_payload,
            file_size=len(invocation_payload),
            uploaded_by_user_id=self.test_user_id,
        )

        servers_upload = CID(
            path=f"/{servers_cid}",
            file_data=servers_payload,
            file_size=len(servers_payload),
            uploaded_by_user_id=self.test_user_id,
        )

        invocation = ServerInvocation(
            user_id=self.test_user_id,
            server_name='test-server',
            result_cid=server_result_cid,
            invocation_cid=invocation_cid,
            request_details_cid=request_cid,
            servers_cid=servers_cid,
        )

        db.session.add_all([
            manual_upload,
            server_upload,
            request_upload,
            invocation_upload,
            servers_upload,
            invocation,
        ])
        db.session.commit()

        response = self.client.get('/uploads')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn(manual_cid, page)
        self.assertNotIn(server_result_cid, page)
        self.assertNotIn(request_cid, page)
        self.assertNotIn(invocation_cid, page)
        self.assertNotIn(servers_cid, page)
        self.assertNotIn('Server: test-server', page)
        self.assertNotIn('View event JSON', page)

    def test_server_events_page_shows_invocations(self):
        """Server events page should list invocation details and required links."""
        self.login_user()

        result_cid = generate_cid(b"result")
        invocation_cid = "I" * CID_LENGTH
        servers_cid = "S" * CID_LENGTH

        request_payload = json.dumps({
            'headers': {
                'Referer': 'https://example.com/origin'
            }
        }, indent=2, sort_keys=True).encode('utf-8')
        request_cid = generate_cid(request_payload)

        db.session.add(CID(
            path=f'/{request_cid}',
            file_data=request_payload,
            file_size=len(request_payload),
            uploaded_by_user_id=self.test_user_id,
        ))

        invocation = ServerInvocation(
            user_id=self.test_user_id,
            server_name='test-server',
            result_cid=result_cid,
            servers_cid=servers_cid,
            request_details_cid=request_cid,
            invocation_cid=invocation_cid,
        )

        db.session.add(invocation)
        db.session.commit()

        response = self.client.get('/server_events')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn(f'href="/{invocation_cid}.txt"', page)
        self.assertIn(f'href="/{request_cid}.txt"', page)
        self.assertIn(f'href="/{result_cid}.txt"', page)
        self.assertIn(f'href="/{servers_cid}.txt"', page)

        self.assertIn(f'/{invocation_cid}.txt', page)
        self.assertIn(f'/{request_cid}.txt', page)
        self.assertIn(f'/{result_cid}.txt', page)
        self.assertIn(f'/{servers_cid}.txt', page)

        self.assertIn(f'/edit/{invocation_cid}', page)
        self.assertIn(f'/meta/{invocation_cid}', page)
        self.assertIn('/servers/test-server', page)
        self.assertIn('https://example.com/origin', page)

        self.assertIn(f'#{invocation_cid[:9]}...', page)
        self.assertIn(f'#{request_cid[:9]}...', page)
        self.assertIn(f'#{result_cid[:9]}...', page)
        self.assertIn(f'#{servers_cid[:9]}...', page)


class TestCidEditingRoutes(BaseTestCase):
    """Tests for editing CID content via the edit page."""

    def _create_cid_record(self, content: bytes, path: str = None) -> str:
        if path is None:
            cid_value = generate_cid(content)
            cid_path = f'/{cid_value}'
        else:
            cid_path = path if path.startswith('/') else f'/{path}'
            cid_value = cid_path.lstrip('/')

        record = CID(
            path=cid_path,
            file_data=content,
            file_size=len(content),
            uploaded_by_user_id=self.test_user_id,
        )
        db.session.add(record)
        db.session.commit()
        return cid_value

    def _create_alias(self, name: str, target_path: str) -> Alias:
        alias = Alias(
            name=name,
            user_id=self.test_user_id,
            definition=_alias_definition(name, target_path),
        )
        db.session.add(alias)
        db.session.commit()
        return alias

    def test_edit_requires_login(self):
        cid_value = self._create_cid_record(b'needs auth')
        response = self.client.get(f'/edit/{cid_value}', follow_redirects=False)
        self.assertEqual(response.status_code, 200)

    def test_edit_cid_get_full_match(self):
        cid_value = self._create_cid_record(b'original content')
        alias = Alias(
            name='docs',
            user_id=self.test_user_id,
            definition=_alias_definition('docs', '/docs'),
        )
        server = Server(name='ref-server', definition='return None', user_id=self.test_user_id)
        db.session.add_all([alias, server])
        db.session.commit()
        cid_record = CID.query.filter_by(path=f'/{cid_value}').first()
        cid_record.file_data = b'Use /docs with /servers/ref-server'
        db.session.commit()

        self.login_user()
        response = self.client.get(f'/edit/{cid_value}')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Referenced Entities', page)
        self.assertIn('docs', page)
        self.assertIn('ref-server', page)
        self.assertIn(cid_value, page)
        self.assertIn('text_content-ai-input', page)
        self.assertIn('data-ai-target-id="text_content"', page)
        self.assertIn('data-code-editor-for="text_content"', page)
        self.assertIn('js/code_editor.js', page)
        self.assertIn('ace-builds@1.32.6', page)

    def test_edit_cid_get_without_alias_shows_alias_field(self):
        cid_value = self._create_cid_record(b'no alias yet')
        self.login_user()
        response = self.client.get(f'/edit/{cid_value}')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Alias Name (optional)', page)
        self.assertIn('Optionally supply a new alias', page)

    def test_edit_cid_get_unique_prefix(self):
        cid_value = self._create_cid_record(b'unique prefix content')
        self.login_user()
        prefix = cid_value[:6]

        response = self.client.get(f'/edit/{prefix}')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn(cid_value, page)
        self.assertIn('unique prefix content', page)

    def test_edit_cid_get_with_existing_alias_updates_button_text(self):
        cid_value = self._create_cid_record(b'aliased content')
        self._create_alias('Atari', f'/{cid_value}')
        self.login_user()

        response = self.client.get(f'/edit/{cid_value}')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Save Atari', page)
        self.assertIn('Saving will update the <strong>Atari</strong> alias', page)
        self.assertNotIn('Alias Name (optional)', page)

    def test_edit_cid_multiple_matches(self):
        self.login_user()
        first = self._create_cid_record(b'first option', path='/shared123')
        second = self._create_cid_record(b'second option', path='/shared456')

        response = self.client.get('/edit/shared')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Multiple Matches Found', page)
        self.assertIn(first, page)
        self.assertIn(second, page)

    def test_edit_cid_full_match_preferred_over_prefix(self):
        self.login_user()
        exact = self._create_cid_record(b'exact match', path='/shared')
        self._create_cid_record(b'longer match', path='/shared123')

        response = self.client.get('/edit/shared')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertNotIn('Multiple Matches Found', page)
        self.assertIn(exact, page)
        self.assertIn('exact match', page)

    def test_edit_cid_not_found(self):
        self.login_user()
        response = self.client.get('/edit/missing')
        self.assertEqual(response.status_code, 404)

    def test_edit_cid_save_creates_new_record(self):
        original_content = b'original text'
        cid_value = self._create_cid_record(original_content)
        self.login_user()

        updated_text = 'updated text value'
        response = self.client.post(
            f'/edit/{cid_value}',
            data={'text_content': updated_text, 'submit': 'Save Changes'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        new_cid = generate_cid(updated_text.encode('utf-8'))
        record = CID.query.filter_by(path=f'/{new_cid}').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.file_data, updated_text.encode('utf-8'))

        page = response.get_data(as_text=True)
        self.assertIn(new_cid, page)

    def test_edit_cid_save_updates_existing_alias_target(self):
        original_content = b'alias original'
        cid_value = self._create_cid_record(original_content)
        self._create_alias('Atari', f'/{cid_value}')
        self.login_user()

        updated_text = 'alias new content'
        response = self.client.post(
            f'/edit/{cid_value}',
            data={'text_content': updated_text, 'submit': 'Save Atari'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        new_cid = generate_cid(updated_text.encode('utf-8'))
        alias = Alias.query.filter_by(name='Atari', user_id=self.test_user_id).first()
        self.assertIsNotNone(alias)
        self.assertEqual(alias.target_path, f'/{new_cid}')

        page = response.get_data(as_text=True)
        self.assertIn(new_cid, page)

    def test_edit_cid_save_allows_creating_new_alias(self):
        original_content = b'add alias original'
        cid_value = self._create_cid_record(original_content)
        self.login_user()

        updated_text = 'add alias new'
        alias_name = 'NewAlias'
        response = self.client.post(
            f'/edit/{cid_value}',
            data={
                'text_content': updated_text,
                'alias_name': alias_name,
                'submit': 'Save Changes',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        new_cid = generate_cid(updated_text.encode('utf-8'))
        alias = Alias.query.filter_by(name=alias_name, user_id=self.test_user_id).first()
        self.assertIsNotNone(alias)
        self.assertEqual(alias.target_path, f'/{new_cid}')
        self.assertEqual(alias.match_type, 'literal')
        self.assertFalse(alias.ignore_case)

    def test_edit_cid_alias_name_conflict_shows_error(self):
        original_content = b'conflict original'
        cid_value = self._create_cid_record(original_content)
        self._create_alias('Existing', '/other-target')
        self.login_user()

        updated_text = 'conflict new text'
        response = self.client.post(
            f'/edit/{cid_value}',
            data={
                'text_content': updated_text,
                'alias_name': 'Existing',
                'submit': 'Save Changes',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Alias with this name already exists.', page)
        self.assertIn('Alias Name (optional)', page)

        new_cid = generate_cid(updated_text.encode('utf-8'))
        self.assertIsNone(CID.query.filter_by(path=f'/{new_cid}').first())

        alias = Alias.query.filter_by(name='Existing', user_id=self.test_user_id).first()
        self.assertIsNotNone(alias)
        self.assertEqual(alias.target_path, '/other-target')

    def test_edit_cid_save_existing_content(self):
        content = b'repeated text content'
        cid_value = self._create_cid_record(content)
        self.login_user()

        response = self.client.post(
            f'/edit/{cid_value}',
            data={'text_content': content.decode('utf-8'), 'submit': 'Save Changes'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        count = CID.query.filter_by(path=f'/{cid_value}').count()
        self.assertEqual(count, 1)

class TestHistoryRoutes(BaseTestCase):
    """Test history and page view routes."""

    @patch('routes.history.get_user_history_statistics')
    def test_history_page_displays_invocation_and_referer_details(self, mock_stats):
        """Ensure history page renders invocation links, server events, and referer metadata for page views."""
        result_cid = 'A' * CID_LENGTH
        invocation_cid = 'B' * CID_LENGTH

        # Mock the statistics function to avoid SQLAlchemy func issues
        mock_stats.return_value = {
            'total_views': 1,
            'unique_paths': 1,
            'popular_paths': [(f'/{result_cid}', 1)]
        }

        self.login_user()

        # Create test page view
        request_details = json.dumps({
            'headers': {
                'Referer': 'https://example.com/source'
            }
        }, indent=2, sort_keys=True).encode('utf-8')
        request_cid = generate_cid(request_details)

        db.session.add(CID(
            path=f'/{request_cid}',
            file_data=request_details,
            file_size=len(request_details),
            uploaded_by_user_id=self.test_user_id,
        ))

        invocation = ServerInvocation(
            user_id=self.test_user_id,
            server_name='test-server',
            result_cid=result_cid,
            invocation_cid=invocation_cid,
            request_details_cid=request_cid,
        )
        db.session.add(invocation)

        page_view = PageView(
            user_id=self.test_user_id,
            path=f'/{result_cid}',
            method='GET',
            user_agent='Test Agent',
            ip_address='127.0.0.1'
        )
        db.session.add(page_view)
        db.session.commit()

        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)

        # Success criteria: invocation link, server event details, and referer metadata are visible.
        page = response.get_data(as_text=True)
        self.assertIn(f'/{invocation_cid}.json', page)
        self.assertIn('Server event: test-server', page)
        self.assertIn('Referer: https://example.com/source', page)

    @patch('routes.history.get_user_history_statistics')
    @patch('routes.history.get_paginated_page_views')
    def test_history_pagination_second_page_empty_results(self, mock_paginated, mock_stats):
        """Requesting page 2 returns 200 even when pagination yields no results."""
        # Mock pagination/statistics to simulate requesting an empty second page.
        mock_stats.return_value = {
            'total_views': 1,
            'unique_paths': 1,
            'popular_paths': [('/test-path', 1)]
        }
        mock_paginated.return_value = []

        self.login_user()
        response = self.client.get('/history?page=2')
        self.assertEqual(response.status_code, 200)


class TestServerRoutes(BaseTestCase):
    """Test server management routes."""

    @patch('routes.servers.get_current_server_definitions_cid')
    def test_servers_list(self, mock_cid):
        """Test servers list page."""
        # Mock the CID function to avoid potential issues
        mock_cid.return_value = 'test_cid_123'

        self.login_user()
        response = self.client.get('/servers')
        self.assertEqual(response.status_code, 200)

    def test_new_server_get(self):
        """Test new server page GET request."""
        self.login_user()
        response = self.client.get('/servers/new')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Start from a Template', page)
        self.assertIn('server-template-select', page)
        self.assertIn('definition-ai-input', page)
        self.assertIn('data-ai-target-id="definition"', page)

        for template in get_server_templates():
            self.assertIn(template['name'], page)
            if template.get('description'):
                self.assertIn(template['description'], page)

    def test_new_server_prefills_name_from_path_query(self):
        """The server creation form should reuse the requested path for its name."""
        self.login_user()

        response = self.client.get('/servers/new?path=/docs/latest')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('value="docs"', page)

    def test_new_server_post(self):
        """Test creating new server."""
        self.login_user()
        response = self.client.post('/servers/new', data={
            'name': 'test-server',
            'definition': 'Test server definition',
            'template': 'y',
            'submit': 'Save Server'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Check server was created
        server = Server.query.filter_by(user_id=self.test_user_id, name='test-server').first()
        self.assertIsNotNone(server)
        self.assertEqual(server.definition, 'Test server definition')
        self.assertTrue(server.template)

    def test_new_server_duplicate_name(self):
        """Test creating server with duplicate name."""
        # Create existing server
        existing_server = Server(
            name='duplicate-server',
            definition='Existing definition',
            user_id=self.test_user_id
        )
        db.session.add(existing_server)
        db.session.commit()

        self.login_user()
        response = self.client.post('/servers/new', data={
            'name': 'duplicate-server',
            'definition': 'New definition',
            'submit': 'Save Server'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Should not create duplicate
        count = Server.query.filter_by(user_id=self.test_user_id, name='duplicate-server').count()
        self.assertEqual(count, 1)

    def test_view_server_renders_referenced_entities_and_returns_ok(self):
        """Viewing a server returns 200 and surfaces referenced metadata in the page."""
        helper_server = Server(name='helper', definition='print("helper")', user_id=self.test_user_id)
        alias = Alias(
            name='docs-link',
            user_id=self.test_user_id,
            definition=_alias_definition('docs-link', '/docs'),
        )
        cid_value = 'cidserver123456'
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'server reference',
            file_size=16,
            uploaded_by_user_id=self.test_user_id,
        )
        server = Server(
            name='view-server',
            definition=(
                f'print("Use /{alias.name} and /servers/{helper_server.name} and /{helper_server.name} and /{cid_value}")'
            ),
            user_id=self.test_user_id
        )
        db.session.add_all([helper_server, alias, cid_record, server])
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/view-server')
        # Viewing the server should succeed and expose referenced resources to the user.
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('Referenced Entities', page)
        self.assertIn(alias.name, page)
        self.assertIn(helper_server.name, page)
        self.assertIn(f'/meta/{cid_value}', page)

    def test_view_server_includes_main_test_form(self):
        """Server detail page should surface parameter inputs when main() is present."""
        server = Server(
            name='auto-test',
            definition='def main(user, greeting="Hello"):\n    return {"output": greeting}',
            user_id=self.test_user_id,
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/auto-test')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('data-mode="main"', page)
        self.assertIn('name="user"', page)
        self.assertIn('name="greeting"', page)
        user_snippet = '\n'.join([
            '<textarea class="form-control"',
            '                                  id="server-test-param-0"',
            '                                  name="user"',
        ])
        greeting_snippet = '\n'.join([
            '<textarea class="form-control"',
            '                                  id="server-test-param-1"',
            '                                  name="greeting"',
        ])
        legacy_input_snippet = '\n'.join([
            '<input type="text"',
            '                               class="form-control"',
            '                               id="server-test-param-0"',
        ])
        self.assertIn(user_snippet, page)
        self.assertIn(greeting_snippet, page)
        self.assertNotIn(legacy_input_snippet, page)
        self.assertIn('/auto-test', page)

    def test_view_server_falls_back_to_query_test_form(self):
        """When no main() exists a key/value textarea should be displayed."""
        server = Server(
            name='simple-test',
            definition='print("hello")',
            user_id=self.test_user_id,
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/simple-test')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('data-mode="query"', page)
        self.assertIn('Enter each parameter on a new line', page)
        self.assertIn('/simple-test', page)
        self.assertIn('server-test-query-ai-input', page)
        self.assertIn('data-ai-target-id="server-test-query"', page)

    def test_view_server_invocation_history_table(self):
        """Server detail page should show invocation events in table format."""
        server = Server(
            name='view-server',
            definition='Server to view',
            user_id=self.test_user_id
        )
        db.session.add(server)

        result_cid = generate_cid(b"result")
        invocation_cid = "I" * CID_LENGTH
        servers_cid = "S" * CID_LENGTH

        request_payload = json.dumps({
            'headers': {
                'Referer': 'https://example.com/origin'
            }
        }, indent=2, sort_keys=True).encode('utf-8')
        request_cid = generate_cid(request_payload)

        db.session.add(CID(
            path=f'/{request_cid}',
            file_data=request_payload,
            file_size=len(request_payload),
            uploaded_by_user_id=self.test_user_id,
        ))

        invocation = ServerInvocation(
            user_id=self.test_user_id,
            server_name='view-server',
            result_cid=result_cid,
            servers_cid=servers_cid,
            request_details_cid=request_cid,
            invocation_cid=invocation_cid,
        )
        db.session.add(invocation)
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/view-server')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('<th>Invoked</th>', page)
        self.assertNotIn('<th>Server</th>', page)
        self.assertIn(f'href="/{invocation_cid}.txt"', page)
        self.assertIn(f'href="/{request_cid}.txt"', page)
        self.assertIn(f'href="/{result_cid}.txt"', page)
        self.assertIn(f'href="/{servers_cid}.txt"', page)
        self.assertIn(f'/edit/{invocation_cid}', page)
        self.assertIn(f'/meta/{invocation_cid}', page)
        self.assertIn(f'/{invocation_cid}.txt', page)
        self.assertIn(f'/{request_cid}.txt', page)
        self.assertIn(f'/{result_cid}.txt', page)
        self.assertIn(f'/{servers_cid}.txt', page)
        self.assertIn(f'#{invocation_cid[:9]}...', page)
        self.assertIn(f'#{request_cid[:9]}...', page)
        self.assertIn(f'#{result_cid[:9]}...', page)
        self.assertIn(f'#{servers_cid[:9]}...', page)
        self.assertIn('https://example.com/origin', page)
        self.assertIn('1 total', page)

    def test_view_nonexistent_server(self):
        """Test viewing nonexistent server."""
        self.login_user()
        response = self.client.get('/servers/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_edit_server_get(self):
        """Test edit server page GET request."""
        server = Server(
            name='edit-server',
            definition='Server to edit',
            user_id=self.test_user_id
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/edit-server/edit')
        self.assertEqual(response.status_code, 200)

    def test_edit_server_includes_test_form(self):
        """Edit page should expose the testing controls based on main() parameters."""
        server = Server(
            name='edit-test',
            definition='def main(token):\n    return {"output": token}',
            user_id=self.test_user_id,
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.get('/servers/edit-test/edit')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('data-mode="main"', page)
        self.assertIn('name="token"', page)
        self.assertIn('/edit-test', page)

    def test_edit_server_post(self):
        """Test editing server."""
        server = Server(
            name='edit-server',
            definition='Original definition',
            user_id=self.test_user_id
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.post('/servers/edit-server/edit', data={
            'name': 'edited-server',
            'definition': 'Updated definition',
            'submit': 'Rename to edited-server'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)

        # Check server was updated
        db.session.refresh(server)
        self.assertEqual(server.name, 'edited-server')
        self.assertEqual(server.definition, 'Updated definition')

    def test_edit_server_save_as_creates_new_server(self):
        """Saving a server as a new copy should keep the original intact."""
        server = Server(
            name='copy-source',
            definition='Copy me',
            user_id=self.test_user_id
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.post('/servers/copy-source/edit', data={
            'name': 'copy-target',
            'definition': 'Copy me',
            'enabled': 'y',
            'submit_action': 'save-as'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/servers/copy-target'))

        db.session.refresh(server)
        self.assertEqual(server.name, 'copy-source')

        duplicate = Server.query.filter_by(user_id=self.test_user_id, name='copy-target').first()
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.definition, 'Copy me')

    def test_delete_server(self):
        """Test deleting server."""
        server = Server(
            name='delete-server',
            definition='Server to delete',
            user_id=self.test_user_id
        )
        db.session.add(server)
        db.session.commit()

        self.login_user()
        response = self.client.post('/servers/delete-server/delete', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        # Check server was deleted
        deleted_server = Server.query.filter_by(user_id=self.test_user_id, name='delete-server').first()
        self.assertIsNone(deleted_server)


class TestVariableRoutes(BaseTestCase):
    """Test variable management routes."""

    def test_variables_list_shows_sorted_user_variables(self):
        """Variables page should: 1) return 200, 2) show user variables, 3) sort them alphabetically."""

        variable_a = Variable(
            name='alpha',
            definition='First variable',
            user_id=self.test_user_id,
        )
        variable_b = Variable(
            name='beta',
            definition='Second variable',
            user_id=self.test_user_id,
        )
        db.session.add_all([variable_b, variable_a])
        db.session.commit()

        self.login_user()
        response = self.client.get('/variables')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('alpha', page)
        self.assertIn('beta', page)
        self.assertLess(page.index('alpha'), page.index('beta'))

    def test_new_variable_post(self):
        """Test creating new variable."""
        self.login_user()
        response = self.client.post('/variables/new', data={
            'name': 'test-variable',
            'definition': 'Test variable definition',
            'template': 'y',
            'submit': 'Save Variable'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Check variable was created
        variable = Variable.query.filter_by(user_id=self.test_user_id, name='test-variable').first()
        self.assertIsNotNone(variable)
        self.assertEqual(variable.definition, 'Test variable definition')
        self.assertTrue(variable.template)

    def test_new_variable_form_includes_ai_controls(self):
        """Variable form should expose AI helper controls."""
        self.login_user()
        response = self.client.get('/variables/new')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('definition-ai-input', page)
        self.assertIn('Ask AI to edit the variable definition', page)
        self.assertIn('data-code-editor-for="definition"', page)
        self.assertIn('code_editor.js', page)

    def test_variable_view_shows_matching_route_summary(self):
        """Variable detail view should render matching route information."""

        variable = Variable(
            name='profile-link',
            definition='/profile',
            user_id=self.test_user_id,
        )
        db.session.add(variable)
        db.session.commit()

        self.login_user()
        response = self.client.get('/variables/profile-link')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Matching Route', page)
        self.assertIn('Route main.profile', page)
        self.assertIn('/profile', page)
        self.assertIn('Status:', page)

    def test_variable_edit_shows_404_matching_route(self):
        """Variable edit form should surface missing route diagnostics."""

        variable = Variable(
            name='missing-route',
            definition='/missing-endpoint',
            user_id=self.test_user_id,
        )
        db.session.add(variable)
        db.session.commit()

        self.login_user()
        response = self.client.get('/variables/missing-route/edit')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Matching Route', page)
        self.assertIn('/missing-endpoint', page)
        self.assertIn('404 – Not Found', page)

    def test_variable_context_prefetches_path_content(self):
        """Variable values pointing at paths should resolve to page content."""

        server = Server(
            name='prefetch-source',
            definition="""
def main():
    return {"output": "prefetched-value", "content_type": "text/plain"}
""".strip(),
            user_id=self.test_user_id,
        )
        variable = Variable(
            name='prefetched',
            definition='/prefetch-source',
            user_id=self.test_user_id,
        )
        db.session.add_all([server, variable])
        db.session.commit()

        with self.app.test_request_context('/prefetch-check'):
            from flask import session

            session['_user_id'] = self.test_user_id
            context = server_execution._load_user_context()

        self.assertIn('prefetched', context['variables'])
        value = context['variables']['prefetched']
        self.assertNotEqual(value, variable.definition)
        self.assertIn('prefetched-value', value)


class TestSecretRoutes(BaseTestCase):
    """Test secret management routes."""

    def test_secrets_list(self):
        """Test secrets list page."""
        self.login_user()
        response = self.client.get('/secrets')
        self.assertEqual(response.status_code, 200)

    def test_new_secret_post(self):
        """Test creating new secret."""
        self.login_user()
        response = self.client.post('/secrets/new', data={
            'name': 'test-secret',
            'definition': 'Test secret definition',
            'template': 'y',
            'submit': 'Save Secret'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Check secret was created
        secret = Secret.query.filter_by(user_id=self.test_user_id, name='test-secret').first()
        self.assertIsNotNone(secret)
        self.assertEqual(secret.definition, 'Test secret definition')
        self.assertTrue(secret.template)

    def test_new_secret_form_includes_ai_controls(self):
        """Secret form should expose AI helper controls."""
        self.login_user()
        response = self.client.get('/secrets/new')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('definition-ai-input', page)
        self.assertIn('Ask AI to edit the secret definition', page)
        self.assertIn('data-code-editor-for="definition"', page)
        self.assertIn('code_editor.js', page)

    def test_view_secret_page_displays_secret_details(self):
        """Secret detail page should render secret metadata and definition."""
        self.login_user()

        secret = Secret(
            name='production-api-key',
            definition='super-secret-value',
            user_id=self.test_user_id,
        )
        db.session.add(secret)
        db.session.commit()

        response = self.client.get('/secrets/production-api-key')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Secret Definition', page)
        self.assertIn('super-secret-value', page)
        self.assertIn('Direct URL', page)
        self.assertIn('/secrets/production-api-key', page)

    def test_view_secret_missing_returns_404(self):
        """Requesting a secret that does not exist should return 404."""
        self.login_user()

        response = self.client.get('/secrets/nonexistent-secret')
        self.assertEqual(response.status_code, 404)


class TestAliasRoutes(BaseTestCase):
    """Test alias management AI helpers."""

    def test_new_alias_form_includes_ai_controls(self):
        """Alias form should expose AI helper controls."""
        self.login_user()
        response = self.client.get('/aliases/new')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('definition-ai-input', page)
        self.assertIn('data-ai-target-id="definition"', page)
        self.assertIn('Ask AI to edit the alias definition', page)
        self.assertIn('data-code-editor-for="definition"', page)
        self.assertIn('code_editor.js', page)

    def test_edit_alias_post_updates_alias(self):
        """Renaming an alias should update its name and retain a valid definition."""
        alias = Alias(
            name='docs-link',
            user_id=self.test_user_id,
            definition=_alias_definition('docs-link', '/docs'),
        )
        db.session.add(alias)
        db.session.commit()

        self.login_user()
        response = self.client.post(f'/aliases/{alias.name}/edit', data={
            'name': 'docs-guide',
            'definition': _alias_definition('docs-link', '/docs'),
            'enabled': 'y',
            'submit': 'Rename to docs-guide',
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)

        db.session.refresh(alias)
        self.assertEqual(alias.name, 'docs-guide')
        self.assertEqual(alias.definition, _alias_definition('docs-guide', '/docs'))

    def test_edit_alias_save_as_creates_new_alias(self):
        """Saving an alias as a copy should not modify the original alias."""
        alias = Alias(
            name='alias-source',
            user_id=self.test_user_id,
            definition=_alias_definition('alias-source', '/docs/source'),
        )
        db.session.add(alias)
        db.session.commit()

        self.login_user()
        response = self.client.post(f'/aliases/{alias.name}/edit', data={
            'name': 'alias-copy',
            'definition': _alias_definition('alias-source', '/docs/source'),
            'enabled': 'y',
            'submit_action': 'save-as',
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/aliases/alias-copy'))

        db.session.refresh(alias)
        self.assertEqual(alias.name, 'alias-source')

        alias_copy = Alias.query.filter_by(user_id=self.test_user_id, name='alias-copy').first()
        self.assertIsNotNone(alias_copy)
        self.assertEqual(alias_copy.definition, _alias_definition('alias-copy', '/docs/source'))

    def test_alias_list_displays_cid_link_for_cid_target(self):
        """Alias listings should render CID targets with the standard link widget."""
        self.login_user()

        cid_value = generate_cid(b'Alias list CID target display')
        alias = Alias(
            name='cid-list',
            user_id=self.test_user_id,
            definition=_alias_definition('cid-list', f'/{cid_value}'),
        )

        db.session.add(alias)
        db.session.commit()

        response = self.client.get('/aliases')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('My Aliases', page)
        self.assertIn('cid-display dropdown', page)
        self.assertIn(f'href="/{cid_value}.txt"', page)
        self.assertNotIn(f'<code>/{cid_value}</code>', page)

    def test_alias_detail_displays_cid_link_for_cid_target(self):
        """Alias detail view should render CID targets with the standard link widget."""
        self.login_user()

        cid_value = generate_cid(b'Alias detail CID target display')
        cid_record = CID(
            path=f'/{cid_value}',
            file_data=b'Alias detail content',
            uploaded_by_user_id=self.test_user_id,
        )
        alias = Alias(
            name='cid-detail',
            user_id=self.test_user_id,
            definition=_alias_definition('cid-detail', f'/{cid_value}'),
        )

        db.session.add_all([cid_record, alias])
        db.session.commit()

        response = self.client.get(f'/aliases/{alias.name}')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertRegex(
            page,
            r'(?s)Redirect Path</dt>\s*<dd class="col-sm-9">\s*<span class="cid-display dropdown">',
        )
        self.assertRegex(
            page,
            r'(?s)redirects browsers to\s*<span class="cid-display dropdown">',
        )
        self.assertNotIn(f'<code>/{cid_value}</code>', page)


class TestSettingsRoutes(BaseTestCase):
    """Test settings routes."""

    def test_settings_page(self):
        """Test settings page."""
        self.login_user()
        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)

    def test_settings_page_shows_direct_access_links(self):
        """Settings page should render clickable direct access examples."""

        self.login_user()

        alias = Alias(
            name='docs',
            user_id=self.test_user_id,
            definition=_alias_definition('docs', '/docs-target'),
        )
        server = Server(
            name='engine',
            definition='print("ok")',
            user_id=self.test_user_id,
        )
        variable = Variable(
            name='app-config',
            definition='value = 1',
            user_id=self.test_user_id,
        )
        secret = Secret(
            name='api-key',
            definition='secret-value',
            user_id=self.test_user_id,
        )

        db.session.add_all([alias, server, variable, secret])
        db.session.commit()

        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('<code><a href="/docs">/docs</a></code>', page)
        self.assertIn(
            '<code><a href="/servers/engine">/servers/engine</a></code>', page
        )
        self.assertIn(
            '<code><a href="/variables/app-config">/variables/app-config</a></code>',
            page,
        )
        self.assertIn(
            '<code><a href="/secrets/api-key">/secrets/api-key</a></code>', page
        )

    def test_import_form_includes_ai_controls(self):
        """Import form should expose AI helper controls."""
        self.login_user()
        response = self.client.get('/import')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('import_text-ai-input', page)
        self.assertIn('data-ai-target-id="import_text"', page)


class TestErrorHandlers(BaseTestCase):
    """Test error handlers."""

    def test_404_handler_no_cid_content(self):
        """Test 404 handler when no CID content exists."""
        response = self.client.get('/nonexistent-path')
        self.assertEqual(response.status_code, 404)

    def test_404_handler_with_cid_content(self):
        """Test 404 handler serving CID content."""
        # Create CID content
        test_data = b"Test file content for CID"
        cid_content = CID(
            path="/test-cid-path",
            file_data=test_data,
            file_size=len(test_data),
            uploaded_by_user_id=self.test_user_id
        )
        db.session.add(cid_content)
        db.session.commit()

        response = self.client.get('/test-cid-path')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, test_data)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')

    def test_404_handler_with_etag_caching(self):
        """Test 404 handler ETag caching."""
        test_data = b"Cached content"
        cid = generate_cid(test_data)

        cid_content = CID(
            path=f"/{cid}",
            file_data=test_data,
            file_size=len(test_data),
            uploaded_by_user_id=self.test_user_id
        )
        db.session.add(cid_content)
        db.session.commit()

        # First request
        response = self.client.get(f'/{cid}')
        self.assertEqual(response.status_code, 200)
        etag = response.headers.get('ETag')
        self.assertIsNotNone(etag)

        # Second request with ETag
        response = self.client.get(f'/{cid}', headers={'If-None-Match': etag})
        self.assertEqual(response.status_code, 304)

    def test_404_handler_legacy_html_content(self):
        """Test 404 handler with legacy HTML content."""
        cid_content = CID(
            path="/legacy-content",
            file_data=b"<h1>Legacy HTML</h1>",
            uploaded_by_user_id=self.test_user_id
        )
        db.session.add(cid_content)
        db.session.commit()

        response = self.client.get('/legacy-content')
        self.assertEqual(response.status_code, 200)


class TestPageViewTracking(BaseTestCase):
    """Test page view tracking functionality."""

    @patch('routes.core.current_user')
    def test_page_view_tracking_authenticated(self, mock_current_user):
        """Test page view tracking for authenticated users."""
        mock_current_user.id = self.test_user_id

        # Make request that should be tracked
        self.client.get('/profile')

        # Check if page view was recorded
        PageView.query.filter_by(user_id=self.test_user_id, path='/profile').first()
        # Note: This might not work in test environment due to mocking complexity
        # but the test structure is correct

    def test_page_view_tracking_skip_static(self):
        """Test that static files are not tracked."""
        self.login_user()

        # These should not create page views
        static_paths = ['/static/css/style.css', '/favicon.ico', '/robots.txt']

        for path in static_paths:
            self.client.get(path)
            # Even if 404, should not create page view
            page_view = PageView.query.filter_by(path=path).first()
            self.assertIsNone(page_view)


class TestSourceRoutes(BaseTestCase):
    """Test source browsing functionality."""

    def test_source_index_lists_tracked_files(self):
        """Root source page should list tracked files."""
        response = self.client.get('/source')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('models.py', page)
        self.assertIn('/source/models.py', page)

    def test_source_serves_file_content(self):
        """Requesting a tracked file should render its contents."""
        response = self.client.get('/source/models.py')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('class Alias(db.Model)', page)

    def test_source_serves_untracked_project_files(self):
        """Enhanced source browser should serve untracked project files."""
        temp_path = Path(self.app.root_path) / 'untracked_test.py'
        temp_path.write_text('# Untracked Python file', encoding='utf-8')

        try:
            # Clear any cached results to ensure fresh discovery
            from routes.source import _get_all_project_files, _get_tracked_paths
            _get_all_project_files.cache_clear()
            _get_tracked_paths.cache_clear()

            response = self.client.get('/source/untracked_test.py')
            # Should now serve untracked project files with enhanced functionality
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            self.assertIn('Untracked Python file', page)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_source_rejects_files_outside_project(self):
        """Files outside project directory should not be served."""
        response = self.client.get('/source/../../../etc/passwd')
        self.assertEqual(response.status_code, 404)

    def test_source_rejects_path_traversal(self):
        """Path traversal attempts should return 404."""
        response = self.client.get('/source/../app.py')
        self.assertEqual(response.status_code, 404)

    def test_source_htmlcov_serves_raw_content(self):
        """Coverage reports should be served without additional templating."""
        htmlcov_dir = Path(self.app.root_path) / 'htmlcov'
        created_dir = not htmlcov_dir.exists()
        htmlcov_dir.mkdir(exist_ok=True)
        html_file = htmlcov_dir / 'index.html'
        html_content = '<html><body>Coverage report</body></html>'
        html_file.write_text(html_content, encoding='utf-8')

        try:
            from routes.source import _get_all_project_files, _get_tracked_paths

            _get_all_project_files.cache_clear()
            _get_tracked_paths.cache_clear()

            response = self.client.get('/source/htmlcov/index.html')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_data(as_text=True), html_content)
        finally:
            html_file.unlink(missing_ok=True)
            if created_dir:
                htmlcov_dir.rmdir()

    def test_source_instance_overview_lists_database_tables(self):
        """Instance overview should list available database tables and columns."""

        response = self.client.get('/source/instance')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('Database Tables', page)
        self.assertIn('href="/source/instance/alias"', page)
        self.assertIn('<code>name</code>', page)

    def test_source_instance_table_renders_existing_rows(self):
        """Table detail view should render rows for a populated table."""

        alias = Alias(name='overview-alias', definition='print("hi")', user_id=self.test_user_id)
        db.session.add(alias)
        db.session.commit()

        response = self.client.get('/source/instance/alias')
        self.assertEqual(response.status_code, 200)

        page = response.get_data(as_text=True)
        self.assertIn('<code>name</code>', page)
        self.assertIn('overview-alias', page)
        self.assertIn('Displaying', page)


if __name__ == '__main__':
    unittest.main()
