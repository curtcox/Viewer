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
from cid import CID as ValidatedCID
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
    record_export,
    get_exports,
    update_alias_cid_reference,
    update_cid_references,
)
from models import (
    Alias,
    CID,
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
        cid_record = CID(path='/cid1', file_data=b'data', file_size=len(b'data'))
        db.session.add(cid_record)
        db.session.commit()
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

        db.session.add_all([
            CID(path='/alpha.one', file_data=b'a', file_size=len(b'a')),
            CID(path='/alpha.two', file_data=b'b', file_size=len(b'b')),
            CID(path='/beta.one', file_data=b'c', file_size=len(b'c')),
        ])
        db.session.commit()

        matches = find_cids_by_prefix('alpha')
        self.assertEqual([cid.path for cid in matches], ['/alpha.one', '/alpha.two'])

        # Prefix lookups should stop at the dot separator when present
        dotted_matches = find_cids_by_prefix('alpha.extra')
        self.assertEqual([cid.path for cid in dotted_matches], ['/alpha.one', '/alpha.two'])

    def test_get_uploads_returns_latest_first(self):
        first = CID(path='/first', file_data=b'1', file_size=len(b'1'))
        db.session.add(first)
        db.session.commit()
        second = CID(path='/second', file_data=b'2', file_size=len(b'2'))
        db.session.add(second)
        db.session.commit()

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

        # Create first CID using a valid CID value
        cid_value = ValidatedCID.from_bytes(b'test data').value
        create_cid_record(cid_value, b'test data')

        # Verify it was created
        cid = get_cid_by_path(f'/{cid_value}')
        self.assertIsNotNone(cid)

        # Attempt to create duplicate should raise IntegrityError
        with self.assertRaises(IntegrityError):
            create_cid_record(cid_value, b'different data')

    def test_page_view_helpers(self):
        base_time = datetime.now(timezone.utc)
        views = [
            PageView(
                path='/alpha',
                method='GET',
                user_agent='Agent',
                ip_address='127.0.0.1',
                viewed_at=base_time - timedelta(minutes=5),
            ),
            PageView(
                path='/beta',
                method='POST',
                user_agent='Agent',
                ip_address='127.0.0.1',
                viewed_at=base_time - timedelta(seconds=30),
            ),
            PageView(
                path='/alpha',
                method='GET',
                user_agent='Agent',
                ip_address='127.0.0.1',
                viewed_at=base_time - timedelta(seconds=10),
            ),
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

        cutoff = base_time - timedelta(minutes=1)
        filtered_count = count_page_views(start=cutoff)
        self.assertEqual(filtered_count, 2)

        filtered_unique = count_unique_page_view_paths(start=cutoff)
        self.assertEqual(filtered_unique, 2)

        filtered_popular = get_popular_page_paths(start=cutoff, end=base_time)
        self.assertTrue(filtered_popular)

        filtered_page = paginate_page_views(page=1, per_page=5, start=cutoff, end=base_time)
        self.assertEqual(filtered_page.page, 1)
        self.assertEqual(filtered_page.total, 2)

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

        recent_only = get_server_invocations(start=now - timedelta(minutes=2))
        self.assertEqual([invocation.server_name for invocation in recent_only], ['demo'])

        by_server = get_server_invocations_by_server('demo')
        self.assertEqual(len(by_server), 1)
        self.assertEqual(by_server[0].result_cid, 'cid-first')

        by_result = get_server_invocations_by_result_cids({'cid-first'})
        self.assertEqual(len(by_result), 1)
        self.assertEqual(by_result[0].invocation_cid, 'invoke-1')

        related = find_server_invocations_by_cid('request-1')
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].server_name, 'demo')

    def test_create_server_invocation_accepts_validated_cids(self):
        """create_server_invocation should accept ValidatedCID inputs."""
        result_cid_obj = ValidatedCID.from_bytes(b'result')
        meta = ServerInvocationInput(
            servers_cid=ValidatedCID.from_bytes(b'servers'),
            variables_cid=ValidatedCID.from_bytes(b'vars'),
            secrets_cid=ValidatedCID.from_bytes(b'secrets'),
        )

        invocation = create_server_invocation('srv-cid', result_cid_obj, meta)

        self.assertIsNotNone(invocation.id)
        self.assertEqual(invocation.server_name, 'srv-cid')
        self.assertEqual(invocation.result_cid, result_cid_obj.value)

    def test_server_invocation_cids_wrapper_parses_validated_values(self):
        """ServerInvocation.cids should expose validated CID objects when possible."""
        result_cid = ValidatedCID.from_bytes(b'result-wrapper')
        request_cid = ValidatedCID.from_bytes(b'request-wrapper')
        invocation_cid = ValidatedCID.from_bytes(b'invocation-wrapper')

        invocation = ServerInvocation(
            server_name='wrapper-test',
            result_cid=result_cid.value,
            request_details_cid=request_cid.value,
            invocation_cid=invocation_cid.value,
            servers_cid='not-a-valid-cid',
        )

        parsed = invocation.cids
        self.assertIsNotNone(parsed.result)
        self.assertEqual(parsed.result.value, result_cid.value)
        self.assertIsNotNone(parsed.request_details)
        self.assertEqual(parsed.request_details.value, request_cid.value)
        self.assertIsNotNone(parsed.invocation)
        self.assertEqual(parsed.invocation.value, invocation_cid.value)
        self.assertIsNone(parsed.servers)

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

    def test_update_cid_references_accepts_validated_cids(self):
        """update_cid_references should accept ValidatedCID inputs."""
        old_obj = ValidatedCID.from_bytes(b"old-cid")
        new_obj = ValidatedCID.from_bytes(b"new-cid")

        definition_text = format_primary_alias_line(
            'literal',
            '/docs2',
            f'/{old_obj.value}?download=1',
            alias_name='docs2',
        )
        alias = Alias(name='docs2', definition=definition_text)
        server = Server(
            name='reader2',
            definition=(
                "def main(request):\n"
                f"    return '{old_obj.value}'\n"
            ),
            definition_cid=old_obj.value,
        )
        db.session.add_all([alias, server])
        db.session.commit()

        with patch('cid_utils.save_server_definition_as_cid') as mock_save, patch(
            'cid_utils.store_server_definitions_cid'
        ) as mock_store:
            mock_save.side_effect = lambda definition: 'test-cid-2'
            mock_store.side_effect = lambda: 'stored-2'

            result = update_cid_references(old_obj, new_obj)

        self.assertEqual(result, {'aliases': 1, 'servers': 1})

        db.session.refresh(alias)
        db.session.refresh(server)

        self.assertIn(new_obj.value, alias.definition)
        self.assertNotIn(old_obj.value, alias.definition)
        self.assertIn(new_obj.value, server.definition)
        self.assertNotIn(old_obj.value, server.definition)
        self.assertEqual(server.definition_cid, 'test-cid-2')

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

    def test_update_alias_cid_reference_accepts_validated_cids(self):
        """update_alias_cid_reference should accept ValidatedCID inputs."""
        old_obj = ValidatedCID.from_bytes(b"alias-old")
        new_obj = ValidatedCID.from_bytes(b"alias-new")

        definition_text = format_primary_alias_line(
            'literal',
            '/cidpath',
            f'/{old_obj.value}?download=1',
            alias_name='cidalias',
        )
        alias = Alias(name='cidalias', definition=definition_text)
        db.session.add(alias)
        db.session.commit()

        result = update_alias_cid_reference(old_obj, new_obj, 'cidalias')

        self.assertEqual(result, {'created': False, 'updated': 1})

        db.session.refresh(alias)
        self.assertIn(new_obj.value, alias.definition)
        self.assertNotIn(old_obj.value, alias.definition)

    def test_cid_lookup_helpers(self):
        CID.query.delete()
        db.session.commit()

        cid_gamma = CID(path='/gamma', file_data=b'g', file_size=len(b'g'))
        cid_delta = CID(path='/delta', file_data=b'd', file_size=len(b'd'))
        db.session.add_all([cid_gamma, cid_delta])
        db.session.commit()

        paths = ['/gamma', '/delta']
        records = get_cids_by_paths(paths)
        self.assertEqual({record.path for record in records}, set(paths))

        recent = get_recent_cids(limit=1)
        self.assertEqual([record.path for record in recent], ['/delta'])

        first = get_first_cid()
        self.assertIsNotNone(first)
        self.assertEqual(first.path, '/gamma')
        self.assertEqual(count_cids(), 2)

    def test_record_export_accepts_validated_cid(self):
        """record_export should accept ValidatedCID inputs and persist value."""
        cid_obj = ValidatedCID.from_bytes(b'export-data')

        export = record_export(cid_obj)

        self.assertIsNotNone(export.id)
        self.assertEqual(export.cid, cid_obj.value)

        exports = get_exports(limit=10)
        self.assertTrue(any(e.cid == cid_obj.value for e in exports))

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
