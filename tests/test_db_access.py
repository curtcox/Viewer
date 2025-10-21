"""Tests for database access helper functions."""
import os
import unittest
from datetime import datetime, timedelta, timezone

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import (
    PageView,
    Server,
    ServerInvocation,
    User,
    Variable,
    Secret,
    db,
)
from db_access import (
    count_cids,
    count_page_views,
    count_payments,
    count_secrets,
    count_servers,
    count_variables,
    count_terms_acceptances,
    count_unique_page_view_paths,
    count_user_servers,
    count_user_variables,
    count_user_secrets,
    count_user_page_views,
    count_users,
    create_cid_record,
    create_payment_record,
    create_server_invocation,
    create_terms_acceptance_record,
    find_cids_by_prefix,
    find_entity_interaction,
    find_server_invocations_by_cid,
    get_all_users,
    get_cid_by_path,
    get_cids_by_paths,
    get_entity_interactions,
    get_first_cid,
    get_popular_page_paths,
    get_recent_cids,
    get_secret_by_name,
    get_server_by_name,
    get_user_by_id,
    get_user_profile_data,
    get_user_server_invocations,
    get_user_server_invocations_by_result_cids,
    get_user_server_invocations_by_server,
    get_user_uploads,
    get_variable_by_name,
    load_user_by_id,
    paginate_user_page_views,
    record_entity_interaction,
    save_entity,
    save_page_view,
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

        self.user = User(id='user1', email='user@example.com')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_payment_record(self):
        create_payment_record('annual', 50.0, self.user)
        self.assertTrue(self.user.is_paid)
        self.assertEqual(len(self.user.payments), 1)
        self.assertEqual(self.user.payments[0].plan_type, 'annual')
        self.assertEqual(count_payments(), 1)

    def test_create_terms_acceptance_record(self):
        create_terms_acceptance_record(self.user, '127.0.0.1')
        self.assertTrue(self.user.current_terms_accepted)
        self.assertEqual(len(self.user.terms_acceptances), 1)
        self.assertEqual(self.user.terms_acceptances[0].ip_address, '127.0.0.1')
        self.assertEqual(count_terms_acceptances(), 1)

    def test_get_user_profile_data(self):
        create_payment_record('free', 0.0, self.user)
        create_terms_acceptance_record(self.user, '127.0.0.1')
        data = get_user_profile_data(self.user.id)
        self.assertEqual(len(data['payments']), 1)
        self.assertFalse(data['needs_terms_acceptance'])

    def test_entity_helpers(self):
        server = Server(name='srv', definition='print(1)', user_id=self.user.id)
        variable = Variable(name='var', definition='1', user_id=self.user.id)
        secret = Secret(name='sec', definition='x', user_id=self.user.id)
        db.session.add_all([server, variable, secret])
        db.session.commit()

        self.assertIsNotNone(get_server_by_name(self.user.id, 'srv'))
        self.assertIsNotNone(get_variable_by_name(self.user.id, 'var'))
        self.assertIsNotNone(get_secret_by_name(self.user.id, 'sec'))
        self.assertEqual(count_user_servers(self.user.id), 1)
        self.assertEqual(count_user_variables(self.user.id), 1)
        self.assertEqual(count_user_secrets(self.user.id), 1)
        self.assertEqual(count_servers(), 1)
        self.assertEqual(count_variables(), 1)
        self.assertEqual(count_secrets(), 1)

    def test_server_invocation_and_cid_helpers(self):
        create_cid_record('cid1', b'data', self.user.id)
        self.assertIsNotNone(get_cid_by_path('/cid1'))
        invocation = create_server_invocation(self.user.id, 'srv', 'cid1')
        self.assertIsNotNone(invocation.id)

    def test_find_cids_by_prefix_filters_and_orders_matches(self):
        # Prefix queries should ignore empty input and leading punctuation
        self.assertEqual(find_cids_by_prefix(''), [])
        self.assertEqual(find_cids_by_prefix('/'), [])

        create_cid_record('alpha.one', b'a', self.user.id)
        create_cid_record('alpha.two', b'b', self.user.id)
        create_cid_record('beta.one', b'c', self.user.id)

        matches = find_cids_by_prefix('alpha')
        self.assertEqual([cid.path for cid in matches], ['/alpha.one', '/alpha.two'])

        # Prefix lookups should stop at the dot separator when present
        dotted_matches = find_cids_by_prefix('alpha.extra')
        self.assertEqual([cid.path for cid in dotted_matches], ['/alpha.one', '/alpha.two'])

    def test_get_user_uploads_returns_latest_first(self):
        create_cid_record('first', b'1', self.user.id)
        create_cid_record('second', b'2', self.user.id)

        uploads = get_user_uploads(self.user.id)
        self.assertEqual([cid.path for cid in uploads], ['/second', '/first'])
        self.assertEqual(uploads[0].file_size, len(b'2'))

    def test_page_view_helpers(self):
        views = [
            PageView(user_id=self.user.id, path='/alpha', method='GET', user_agent='Agent', ip_address='127.0.0.1'),
            PageView(user_id=self.user.id, path='/beta', method='POST', user_agent='Agent', ip_address='127.0.0.1'),
            PageView(user_id=self.user.id, path='/alpha', method='GET', user_agent='Agent', ip_address='127.0.0.1'),
        ]
        for view in views:
            save_page_view(view)

        self.assertEqual(count_user_page_views(self.user.id), 3)
        self.assertEqual(count_unique_page_view_paths(self.user.id), 2)
        self.assertEqual(count_page_views(), 3)

        popular = get_popular_page_paths(self.user.id, limit=1)
        self.assertTrue(popular)
        self.assertEqual(popular[0].path, '/alpha')

        pagination = paginate_user_page_views(self.user.id, page=1, per_page=2)
        self.assertEqual(pagination.total, 3)
        self.assertEqual(len(pagination.items), 2)

    def test_server_invocation_helpers(self):
        now = datetime.now(timezone.utc)
        first = ServerInvocation(
            user_id=self.user.id,
            server_name='demo',
            result_cid='cid-first',
            invocation_cid='invoke-1',
            request_details_cid='request-1',
            servers_cid='servers-1',
        )
        first.invoked_at = now
        save_entity(first)

        second = ServerInvocation(
            user_id=self.user.id,
            server_name='other',
            result_cid='cid-second',
        )
        second.invoked_at = now - timedelta(minutes=5)
        save_entity(second)

        all_invocations = get_user_server_invocations(self.user.id)
        self.assertEqual([invocation.server_name for invocation in all_invocations], ['demo', 'other'])

        by_server = get_user_server_invocations_by_server(self.user.id, 'demo')
        self.assertEqual(len(by_server), 1)
        self.assertEqual(by_server[0].result_cid, 'cid-first')

        by_result = get_user_server_invocations_by_result_cids(self.user.id, {'cid-first'})
        self.assertEqual(len(by_result), 1)
        self.assertEqual(by_result[0].invocation_cid, 'invoke-1')

        related = find_server_invocations_by_cid('request-1')
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].server_name, 'demo')

    def test_cid_lookup_helpers(self):
        create_cid_record('gamma', b'g', self.user.id)
        create_cid_record('delta', b'd', self.user.id)

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
            self.user.id,
            'server',
            'demo',
            'save',
            'Created demo',
            'content',
            created_at=timestamp,
        )

        interactions = get_entity_interactions(self.user.id, 'server', 'demo')
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].message, 'Created demo')

        match = find_entity_interaction(
            self.user.id,
            'server',
            'demo',
            'save',
            'Created demo',
            timestamp,
        )
        self.assertIsNotNone(match)

    def test_user_lookup_helpers(self):
        users = get_all_users()
        self.assertEqual([user.id for user in users], [self.user.id])
        self.assertEqual(get_user_by_id(self.user.id).id, self.user.id)
        self.assertEqual(load_user_by_id(self.user.id).id, self.user.id)
        self.assertEqual(count_users(), 1)


if __name__ == '__main__':
    unittest.main()
