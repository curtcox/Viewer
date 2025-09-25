"""Tests for database access helper functions."""
import os
import unittest

# Configure environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from app import app
from models import db, User, Invitation, Server, Variable, Secret
from db_access import (
    create_payment_record,
    create_terms_acceptance_record,
    get_user_profile_data,
    validate_invitation_code,
    get_server_by_name,
    get_variable_by_name,
    get_secret_by_name,
    count_user_servers,
    create_server_invocation,
    create_cid_record,
    get_cid_by_path,
    find_cids_by_prefix,
    get_user_uploads,
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

    def test_create_terms_acceptance_record(self):
        create_terms_acceptance_record(self.user, '127.0.0.1')
        self.assertTrue(self.user.current_terms_accepted)
        self.assertEqual(len(self.user.terms_acceptances), 1)
        self.assertEqual(self.user.terms_acceptances[0].ip_address, '127.0.0.1')

    def test_get_user_profile_data(self):
        create_payment_record('free', 0.0, self.user)
        create_terms_acceptance_record(self.user, '127.0.0.1')
        data = get_user_profile_data(self.user.id)
        self.assertEqual(len(data['payments']), 1)
        self.assertFalse(data['needs_terms_acceptance'])

    def test_validate_invitation_code(self):
        invitation = Invitation(inviter_user_id=self.user.id, invitation_code='ABC123')
        db.session.add(invitation)
        db.session.commit()
        self.assertIsNotNone(validate_invitation_code('ABC123'))
        self.assertIsNone(validate_invitation_code('NOTREAL'))

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


if __name__ == '__main__':
    unittest.main()
