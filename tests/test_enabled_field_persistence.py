"""
Unit tests for the enabled field persistence issue.

This module tests that the enabled field on database models (Alias, Server, Variable, Secret)
properly stores and retrieves False values in the database.

Issue: The enabled field was not persisting False values correctly in SQLite,
always returning True regardless of the value stored.

Fix: Use explicit Boolean() type with server_default in model definitions.
"""

import unittest
from app import create_app
from database import db
from models import Alias, Server, Variable, Secret


class EnabledFieldPersistenceTestCase(unittest.TestCase):
    """Test suite for enabled field persistence across all models."""

    def setUp(self):
        """Set up test fixtures with in-memory SQLite database."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_alias_enabled_false_persists(self):
        """Test that Alias with enabled=False is stored and retrieved correctly."""
        # Create disabled alias
        alias = Alias(
            name='test_alias',
            user_id='user1',
            definition='test definition',
            enabled=False
        )
        db.session.add(alias)
        db.session.commit()

        # Retrieve and verify
        fetched = Alias.query.filter_by(name='test_alias').first()
        self.assertIsNotNone(fetched)
        self.assertFalse(fetched.enabled, "Alias enabled field should be False")

    def test_alias_enabled_true_persists(self):
        """Test that Alias with enabled=True is stored and retrieved correctly."""
        # Create enabled alias
        alias = Alias(
            name='test_alias',
            user_id='user1',
            definition='test definition',
            enabled=True
        )
        db.session.add(alias)
        db.session.commit()

        # Retrieve and verify
        fetched = Alias.query.filter_by(name='test_alias').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Alias enabled field should be True")

    def test_alias_enabled_default_is_true(self):
        """Test that Alias defaults to enabled=True when not specified."""
        # Create alias without specifying enabled
        alias = Alias(
            name='test_alias',
            user_id='user1',
            definition='test definition'
        )
        db.session.add(alias)
        db.session.commit()

        # Retrieve and verify
        fetched = Alias.query.filter_by(name='test_alias').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Alias should default to enabled=True")

    def test_server_enabled_false_persists(self):
        """Test that Server with enabled=False is stored and retrieved correctly."""
        # Create disabled server
        server = Server(
            name='test_server',
            user_id='user1',
            definition='test definition',
            enabled=False
        )
        db.session.add(server)
        db.session.commit()

        # Retrieve and verify
        fetched = Server.query.filter_by(name='test_server').first()
        self.assertIsNotNone(fetched)
        self.assertFalse(fetched.enabled, "Server enabled field should be False")

    def test_server_enabled_true_persists(self):
        """Test that Server with enabled=True is stored and retrieved correctly."""
        # Create enabled server
        server = Server(
            name='test_server',
            user_id='user1',
            definition='test definition',
            enabled=True
        )
        db.session.add(server)
        db.session.commit()

        # Retrieve and verify
        fetched = Server.query.filter_by(name='test_server').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Server enabled field should be True")

    def test_server_enabled_default_is_true(self):
        """Test that Server defaults to enabled=True when not specified."""
        # Create server without specifying enabled
        server = Server(
            name='test_server',
            user_id='user1',
            definition='test definition'
        )
        db.session.add(server)
        db.session.commit()

        # Retrieve and verify
        fetched = Server.query.filter_by(name='test_server').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Server should default to enabled=True")

    def test_variable_enabled_false_persists(self):
        """Test that Variable with enabled=False is stored and retrieved correctly."""
        # Create disabled variable
        variable = Variable(
            name='test_variable',
            user_id='user1',
            definition='test definition',
            enabled=False
        )
        db.session.add(variable)
        db.session.commit()

        # Retrieve and verify
        fetched = Variable.query.filter_by(name='test_variable').first()
        self.assertIsNotNone(fetched)
        self.assertFalse(fetched.enabled, "Variable enabled field should be False")

    def test_variable_enabled_true_persists(self):
        """Test that Variable with enabled=True is stored and retrieved correctly."""
        # Create enabled variable
        variable = Variable(
            name='test_variable',
            user_id='user1',
            definition='test definition',
            enabled=True
        )
        db.session.add(variable)
        db.session.commit()

        # Retrieve and verify
        fetched = Variable.query.filter_by(name='test_variable').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Variable enabled field should be True")

    def test_variable_enabled_default_is_true(self):
        """Test that Variable defaults to enabled=True when not specified."""
        # Create variable without specifying enabled
        variable = Variable(
            name='test_variable',
            user_id='user1',
            definition='test definition'
        )
        db.session.add(variable)
        db.session.commit()

        # Retrieve and verify
        fetched = Variable.query.filter_by(name='test_variable').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Variable should default to enabled=True")

    def test_secret_enabled_false_persists(self):
        """Test that Secret with enabled=False is stored and retrieved correctly."""
        # Create disabled secret
        secret = Secret(
            name='test_secret',
            user_id='user1',
            definition='test definition',
            enabled=False
        )
        db.session.add(secret)
        db.session.commit()

        # Retrieve and verify
        fetched = Secret.query.filter_by(name='test_secret').first()
        self.assertIsNotNone(fetched)
        self.assertFalse(fetched.enabled, "Secret enabled field should be False")

    def test_secret_enabled_true_persists(self):
        """Test that Secret with enabled=True is stored and retrieved correctly."""
        # Create enabled secret
        secret = Secret(
            name='test_secret',
            user_id='user1',
            definition='test definition',
            enabled=True
        )
        db.session.add(secret)
        db.session.commit()

        # Retrieve and verify
        fetched = Secret.query.filter_by(name='test_secret').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Secret enabled field should be True")

    def test_secret_enabled_default_is_true(self):
        """Test that Secret defaults to enabled=True when not specified."""
        # Create secret without specifying enabled
        secret = Secret(
            name='test_secret',
            user_id='user1',
            definition='test definition'
        )
        db.session.add(secret)
        db.session.commit()

        # Retrieve and verify
        fetched = Secret.query.filter_by(name='test_secret').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.enabled, "Secret should default to enabled=True")

    def test_multiple_entities_mixed_enabled_states(self):
        """Test multiple entities with mixed enabled states."""
        # Create entities with different enabled states
        alias_enabled = Alias(name='alias1', user_id='user1', definition='def1', enabled=True)
        alias_disabled = Alias(name='alias2', user_id='user1', definition='def2', enabled=False)

        server_enabled = Server(name='server1', user_id='user1', definition='def1', enabled=True)
        server_disabled = Server(name='server2', user_id='user1', definition='def2', enabled=False)

        variable_enabled = Variable(name='var1', user_id='user1', definition='def1', enabled=True)
        variable_disabled = Variable(name='var2', user_id='user1', definition='def2', enabled=False)

        secret_enabled = Secret(name='secret1', user_id='user1', definition='def1', enabled=True)
        secret_disabled = Secret(name='secret2', user_id='user1', definition='def2', enabled=False)

        db.session.add_all([
            alias_enabled, alias_disabled,
            server_enabled, server_disabled,
            variable_enabled, variable_disabled,
            secret_enabled, secret_disabled
        ])
        db.session.commit()

        # Verify all enabled entities
        self.assertTrue(Alias.query.filter_by(name='alias1').first().enabled)
        self.assertTrue(Server.query.filter_by(name='server1').first().enabled)
        self.assertTrue(Variable.query.filter_by(name='var1').first().enabled)
        self.assertTrue(Secret.query.filter_by(name='secret1').first().enabled)

        # Verify all disabled entities
        self.assertFalse(Alias.query.filter_by(name='alias2').first().enabled)
        self.assertFalse(Server.query.filter_by(name='server2').first().enabled)
        self.assertFalse(Variable.query.filter_by(name='var2').first().enabled)
        self.assertFalse(Secret.query.filter_by(name='secret2').first().enabled)

    def test_enabled_field_update_from_true_to_false(self):
        """Test updating enabled field from True to False."""
        # Create enabled alias
        alias = Alias(name='test_alias', user_id='user1', definition='def', enabled=True)
        db.session.add(alias)
        db.session.commit()

        # Update to disabled
        alias.enabled = False
        db.session.commit()

        # Retrieve and verify
        fetched = Alias.query.filter_by(name='test_alias').first()
        self.assertFalse(fetched.enabled, "Alias should be disabled after update")

    def test_enabled_field_update_from_false_to_true(self):
        """Test updating enabled field from False to True."""
        # Create disabled alias
        alias = Alias(name='test_alias', user_id='user1', definition='def', enabled=False)
        db.session.add(alias)
        db.session.commit()

        # Update to enabled
        alias.enabled = True
        db.session.commit()

        # Retrieve and verify
        fetched = Alias.query.filter_by(name='test_alias').first()
        self.assertTrue(fetched.enabled, "Alias should be enabled after update")

    def test_query_filter_by_enabled_false(self):
        """Test querying for disabled entities."""
        # Create mix of enabled and disabled entities
        alias1 = Alias(name='alias1', user_id='user1', definition='def1', enabled=True)
        alias2 = Alias(name='alias2', user_id='user1', definition='def2', enabled=False)
        alias3 = Alias(name='alias3', user_id='user1', definition='def3', enabled=False)

        db.session.add_all([alias1, alias2, alias3])
        db.session.commit()

        # Query for disabled aliases
        disabled_aliases = Alias.query.filter_by(enabled=False).all()
        self.assertEqual(len(disabled_aliases), 2, "Should find 2 disabled aliases")

        disabled_names = {a.name for a in disabled_aliases}
        self.assertEqual(disabled_names, {'alias2', 'alias3'})

    def test_query_filter_by_enabled_true(self):
        """Test querying for enabled entities."""
        # Create mix of enabled and disabled entities
        alias1 = Alias(name='alias1', user_id='user1', definition='def1', enabled=True)
        alias2 = Alias(name='alias2', user_id='user1', definition='def2', enabled=False)
        alias3 = Alias(name='alias3', user_id='user1', definition='def3', enabled=True)

        db.session.add_all([alias1, alias2, alias3])
        db.session.commit()

        # Query for enabled aliases for this specific user
        enabled_aliases = Alias.query.filter_by(enabled=True, user_id='user1').all()
        self.assertEqual(len(enabled_aliases), 2, "Should find 2 enabled aliases")

        enabled_names = {a.name for a in enabled_aliases}
        self.assertEqual(enabled_names, {'alias1', 'alias3'})

    def test_raw_sql_query_for_disabled_entities(self):
        """Test that raw SQL queries also return correct enabled values."""
        # Create disabled alias
        alias = Alias(name='test_alias', user_id='user1', definition='def', enabled=False)
        db.session.add(alias)
        db.session.commit()

        # Query using raw SQL
        result = db.session.execute(
            db.text("SELECT name, enabled FROM alias WHERE name='test_alias'")
        ).fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'test_alias')
        # SQLite stores boolean as 0 or 1
        self.assertEqual(result[1], 0, "Raw SQL should return 0 for disabled entity")


if __name__ == '__main__':
    unittest.main()
