"""Tests for database access helper functions."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from alias_definition import format_primary_alias_line
from app import app
from db_access import (
    count_cids,
    count_page_views,
    count_secrets,
    count_servers,
    count_unique_page_view_paths,
    count_variables,
    create_cid_record,
    create_server_invocation,
    find_cids_by_prefix,
    find_entity_interaction,
    find_server_invocations_by_cid,
    get_cid_by_path,
    get_cids_by_paths,
    get_entity_interactions,
    get_first_cid,
    get_popular_page_paths,
    get_recent_cids,
    get_secret_by_name,
    get_server_by_name,
    get_server_invocations,
    get_server_invocations_by_result_cids,
    get_server_invocations_by_server,
    get_uploads,
    get_variable_by_name,
    EntityInteractionLookup,
    EntityInteractionRequest,
    ServerInvocationInput,
    paginate_page_views,
    record_entity_interaction,
    save_entity,
    save_page_view,
    update_alias_cid_reference,
    update_cid_references,
)
from models import (
    Alias,
    PageView,
    Secret,
    Server,
    ServerInvocation,
    Variable,
    db,
)


class TestDBAccess(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.app_context = self.app.app_context()
        self.app_context.push()

        self.user_id = 'user1'

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_entity_helpers(self):
        server = Server(name='srv', definition='print(1)')
        variable = Variable(name='var', definition='1')
        secret = Secret(name='sec', definition='x')
        db.session.add_all([server, variable, secret])
        db.session.commit()

        self.assertIsNotNone(get_server_by_name('srv'))
        self.assertIsNotNone(get_variable_by_name('var'))
        self.assertIsNotNone(get_secret_by_name('sec'))
        self.assertEqual(count_servers(), 1)
        self.assertEqual(count_variables(), 1)
        self.assertEqual(count_secrets(), 1)

    def test_server_invocation_and_cid_helpers(self):
        create_cid_record('cid1', b'data')
        self.assertIsNotNone(get_cid_by_path('/cid1'))
        invocation = create_server_invocation(
            'srv',
            'cid1',
            ServerInvocationInput(),
        )
        self.assertIsNotNone(invocation.id)

    def test_find_cids_by_prefix_filters_and_orders_matches(self):
        # Prefix queries should ignore empty input and leading punctuation
        self.assertEqual(find_cids_by_prefix(''), [])
        self.assertEqual(find_cids_by_prefix('/'), [])

        create_cid_record('alpha.one', b'a')
        create_cid_record('alpha.two', b'b')
        create_cid_record('beta.one', b'c')

        matches = find_cids_by_prefix('alpha')
        self.assertEqual([cid.path for cid in matches], ['/alpha.one', '/alpha.two'])

        # Prefix lookups should stop at the dot separator when present
        dotted_matches = find_cids_by_prefix('alpha.extra')
        self.assertEqual([cid.path for cid in dotted_matches], ['/alpha.one', '/alpha.two'])

    def test_get_uploads_returns_latest_first(self):
        create_cid_record('first', b'1')
        create_cid_record('second', b'2')

        uploads = get_uploads()
        self.assertEqual([cid.path for cid in uploads], ['/second', '/first'])
        self.assertEqual(uploads[0].file_size, len(b'2'))

    def test_duplicate_cid_creation_raises_integrity_error(self):
        """Test that creating a duplicate CID raises IntegrityError.

        This test ensures that attempting to create a CID with a path
        that already exists will raise an IntegrityError due to the
        UNIQUE constraint on the path column.
        """
        from sqlalchemy.exc import IntegrityError

        # Create first CID
        create_cid_record('test_cid', b'test data')

        # Verify it was created
        cid = get_cid_by_path('/test_cid')
        self.assertIsNotNone(cid)

        # Attempt to create duplicate should raise IntegrityError
        with self.assertRaises(IntegrityError):
            create_cid_record('test_cid', b'different data')

    def test_page_view_helpers(self):
        views = [
            PageView(path='/alpha', method='GET', user_agent='Agent', ip_address='127.0.0.1'),
            PageView(path='/beta', method='POST', user_agent='Agent', ip_address='127.0.0.1'),
            PageView(path='/alpha', method='GET', user_agent='Agent', ip_address='127.0.0.1'),
        ]
        for view in views:
            save_page_view(view)

        self.assertEqual(count_page_views(), 3)
        self.assertEqual(count_unique_page_view_paths(), 2)

        popular = get_popular_page_paths(limit=1)
        self.assertTrue(popular)
        self.assertEqual(popular[0].path, '/alpha')

        pagination = paginate_page_views(page=1, per_page=2)
        self.assertEqual(pagination.total, 3)
        self.assertEqual(len(pagination.items), 2)

    def test_server_invocation_helpers(self):
        now = datetime.now(timezone.utc)
        first = ServerInvocation(
            server_name='demo',
            result_cid='cid-first',
            invocation_cid='invoke-1',
            request_details_cid='request-1',
            servers_cid='servers-1',
        )
        first.invoked_at = now
        save_entity(first)

        second = ServerInvocation(
            server_name='other',
            result_cid='cid-second',
        )
        second.invoked_at = now - timedelta(minutes=5)
        save_entity(second)

        all_invocations = get_server_invocations()
        self.assertEqual([invocation.server_name for invocation in all_invocations], ['demo', 'other'])

        by_server = get_server_invocations_by_server('demo')
        self.assertEqual(len(by_server), 1)
        self.assertEqual(by_server[0].result_cid, 'cid-first')

        by_result = get_server_invocations_by_result_cids({'cid-first'})
        self.assertEqual(len(by_result), 1)
        self.assertEqual(by_result[0].invocation_cid, 'invoke-1')

        related = find_server_invocations_by_cid('request-1')
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].server_name, 'demo')

    def test_update_cid_references_updates_alias_and_server_records(self):
        old_cid = 'oldcid123456'
        new_cid = 'newcid789012'

        definition_text = format_primary_alias_line(
            'literal',
            '/docs',
            f'/{old_cid}?download=1',
            alias_name='docs',
        )
        definition_text = (
            f"{definition_text}\n# Link to legacy {old_cid} content"
        )
        alias = Alias(
            name='docs',
            definition=definition_text,
        )
        server = Server(
            name='reader',
            definition=(
                "def main(request):\n"
                f"    return '{old_cid}'\n"
            ),
            definition_cid=old_cid,
        )
        db.session.add_all([alias, server])
        db.session.commit()

        with patch('cid_utils.save_server_definition_as_cid') as mock_save, patch(
            'cid_utils.store_server_definitions_cid'
        ) as mock_store:
            mock_save.side_effect = lambda definition: 'test-cid'
            mock_store.side_effect = lambda: 'stored'

            result = update_cid_references(old_cid, new_cid)

        self.assertEqual(result, {'aliases': 1, 'servers': 1})

        db.session.refresh(alias)
        db.session.refresh(server)

        self.assertIn(new_cid, alias.target_path)
        self.assertNotIn(old_cid, alias.target_path)
        self.assertIn(new_cid, alias.definition)
        self.assertNotIn(old_cid, alias.definition)
        self.assertEqual(alias.match_pattern, '/docs')
        self.assertEqual(alias.match_type, 'literal')
        self.assertFalse(alias.ignore_case)

        self.assertIn(new_cid, server.definition)
        self.assertNotIn(old_cid, server.definition)
        self.assertEqual(server.definition_cid, 'test-cid')

        mock_save.assert_called_once()
        mock_store.assert_called_once()

    def test_update_alias_cid_reference_updates_existing_alias(self):
        definition_text = format_primary_alias_line(
            'regex',
            '/custom',
            '/legacycid?download=1',
            ignore_case=True,
            alias_name='release',
        )
        definition_text = (
            f"{definition_text}\n# legacy release pointer legacycid"
        )
        alias = Alias(
            name='release',
            definition=definition_text,
        )
        db.session.add(alias)
        db.session.commit()

        result = update_alias_cid_reference('legacycid', 'latestcid', 'release')

        self.assertEqual(result, {'created': False, 'updated': 1})

        db.session.refresh(alias)
        self.assertEqual(alias.target_path, '/latestcid?download=1')
        self.assertIn('latestcid', alias.definition)
        self.assertNotIn('legacycid', alias.definition)
        self.assertEqual(alias.match_type, 'literal')
        self.assertEqual(alias.match_pattern, '/release')
        self.assertTrue(alias.ignore_case)

    def test_update_alias_cid_reference_creates_alias_when_missing(self):
        result = update_alias_cid_reference('unused', 'freshcid', 'latest')

        self.assertEqual(result, {'created': True, 'updated': 1})

        alias = Alias.query.filter_by(name='latest').first()
        self.assertIsNotNone(alias)
        self.assertEqual(alias.target_path, '/freshcid')
        self.assertIn('/freshcid', alias.definition)
        self.assertEqual(alias.match_type, 'literal')
        self.assertEqual(alias.match_pattern, '/latest')

    def test_cid_lookup_helpers(self):
        create_cid_record('gamma', b'g')
        create_cid_record('delta', b'd')

        paths = ['/gamma', '/delta']
        records = get_cids_by_paths(paths)
        self.assertEqual({record.path for record in records}, set(paths))

        recent = get_recent_cids(limit=1)
        self.assertEqual([record.path for record in recent], ['/delta'])

        first = get_first_cid()
        self.assertIsNotNone(first)
        self.assertEqual(first.path, '/gamma')
        self.assertEqual(count_cids(), 2)

    def test_entity_interaction_helpers(self):
        timestamp = datetime.now(timezone.utc)
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='server',
                entity_name='demo',
                action='save',
                message='Created demo',
                content='content',
                created_at=timestamp,
            )
        )

        interactions = get_entity_interactions('server', 'demo')
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].message, 'Created demo')

        match = find_entity_interaction(
            EntityInteractionLookup(
                entity_type='server',
                entity_name='demo',
                action='save',
                message='Created demo',
                created_at=timestamp,
            )
        )
        self.assertIsNotNone(match)


if __name__ == '__main__':
    unittest.main()
