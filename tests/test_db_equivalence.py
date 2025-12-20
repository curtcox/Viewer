# tests/test_db_equivalence.py
"""Database equivalence tests ensuring memory and disk databases behave identically."""

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database import db
from models import (
    Alias,
    CID,
    EntityInteraction,
    Export,
    PageView,
    Secret,
    Server,
    ServerInvocation,
    Variable,
)


@pytest.mark.db_equivalence
class TestServerEquivalence:
    """Test Server model behaves identically in both database modes."""

    def test_create_server_equivalence(self, memory_db_app, disk_db_app):
        """Creating a server produces equivalent results."""
        server_data = {
            "name": "test-server",
            "definition": "test definition",
            "enabled": True,
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(**server_data)
                db.session.add(server)
                db.session.commit()
                results[name] = {
                    "name": server.name,
                    "definition": server.definition,
                    "enabled": server.enabled,
                }

        assert results["memory"] == results["disk"]

    def test_query_server_equivalence(self, memory_db_app, disk_db_app):
        """Querying servers produces equivalent results."""
        servers = [
            {"name": "server-a", "definition": "def a", "enabled": True},
            {"name": "server-b", "definition": "def b", "enabled": False},
            {"name": "server-c", "definition": "def c", "enabled": True},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

                # Filter out default 'ai_stub' server if present
                query = Server.query.filter(Server.name != "ai_stub")

                results[name] = {
                    "count": query.count(),
                    "enabled": query.filter_by(enabled=True).count(),
                    "names": [s.name for s in query.order_by(Server.name).all()],
                }

        assert results["memory"] == results["disk"]

    def test_update_server_equivalence(self, memory_db_app, disk_db_app):
        """Updating a server produces equivalent results."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                server = Server(name="update-test", definition="original")
                db.session.add(server)
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server.query.filter_by(name="update-test").first()
                server.definition = "updated"
                db.session.commit()
                results[name] = server.definition

        assert results["memory"] == results["disk"] == "updated"

    def test_delete_server_equivalence(self, memory_db_app, disk_db_app):
        """Deleting a server produces equivalent results."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                server = Server(name="delete-test", definition="to delete")
                db.session.add(server)
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server.query.filter_by(name="delete-test").first()
                db.session.delete(server)
                db.session.commit()
                results[name] = Server.query.filter_by(name="delete-test").count()

        assert results["memory"] == results["disk"] == 0


@pytest.mark.db_equivalence
class TestAliasEquivalence:
    """Test Alias model behaves identically in both database modes."""

    def test_create_alias_equivalence(self, memory_db_app, disk_db_app):
        """Creating an alias produces equivalent results."""
        alias_data = {"name": "test-alias", "definition": "/api/test", "enabled": True}

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                alias = Alias(**alias_data)
                db.session.add(alias)
                db.session.commit()
                results[name] = {
                    "name": alias.name,
                    "definition": alias.definition,
                    "enabled": alias.enabled,
                }

        assert results["memory"] == results["disk"]

    def test_alias_ordering_equivalence(self, memory_db_app, disk_db_app):
        """Alias ordering is equivalent in both databases."""
        aliases = [
            {"name": "z-alias", "definition": "/z"},
            {"name": "a-alias", "definition": "/a"},
            {"name": "m-alias", "definition": "/m"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for a in aliases:
                    db.session.add(Alias(**a))
                db.session.commit()

                # Filter out default aliases 'ai' and 'CSS'
                query = Alias.query.filter(Alias.name.notin_(["ai", "CSS"]))
                results[name] = [a.name for a in query.order_by(Alias.name).all()]

        assert results["memory"] == results["disk"]
        assert results["memory"] == ["a-alias", "m-alias", "z-alias"]


@pytest.mark.db_equivalence
class TestVariableEquivalence:
    """Test Variable model behaves identically in both database modes."""

    def test_create_variable_equivalence(self, memory_db_app, disk_db_app):
        """Creating a variable produces equivalent results."""
        var_data = {"name": "TEST_VAR", "definition": "test_value", "enabled": True}

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                var = Variable(**var_data)
                db.session.add(var)
                db.session.commit()
                results[name] = {
                    "name": var.name,
                    "definition": var.definition,
                    "enabled": var.enabled,
                }

        assert results["memory"] == results["disk"]

    def test_variable_unique_constraint_equivalence(self, memory_db_app, disk_db_app):
        """Unique constraint behavior is equivalent in both databases."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                var1 = Variable(name="UNIQUE_VAR", definition="first")
                db.session.add(var1)
                db.session.commit()

                var2 = Variable(name="UNIQUE_VAR", definition="second")
                db.session.add(var2)
                with pytest.raises(IntegrityError):
                    db.session.commit()
                db.session.rollback()


@pytest.mark.db_equivalence
class TestSecretEquivalence:
    """Test Secret model behaves identically in both database modes."""

    def test_create_secret_equivalence(self, memory_db_app, disk_db_app):
        """Creating a secret produces equivalent results."""
        secret_data = {
            "name": "API_KEY",
            "definition": "secret-value-123",
            "enabled": True,
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                secret = Secret(**secret_data)
                db.session.add(secret)
                db.session.commit()
                results[name] = {
                    "name": secret.name,
                    "definition": secret.definition,
                    "enabled": secret.enabled,
                }

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestCIDEquivalence:
    """Test CID model behaves identically in both database modes."""

    def test_create_cid_equivalence(self, memory_db_app, disk_db_app):
        """Creating a CID record produces equivalent results."""
        cid_data = {
            "path": "/cid/test123",
            "file_data": b"test binary data",
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(**cid_data)
                db.session.add(cid)
                db.session.commit()
                results[name] = {
                    "path": cid.path,
                    "file_data": cid.file_data,
                    "file_size": cid.file_size,
                }

        assert results["memory"] == results["disk"]

    def test_cid_binary_data_equivalence(self, memory_db_app, disk_db_app):
        """Binary data storage is equivalent in both databases."""
        binary_data = bytes(range(256))  # All possible byte values

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(path="/cid/binary", file_data=binary_data)
                db.session.add(cid)
                db.session.commit()

                retrieved = CID.query.filter_by(path="/cid/binary").first()
                results[name] = retrieved.file_data

        assert results["memory"] == results["disk"] == binary_data

    def test_cid_large_data_equivalence(self, memory_db_app, disk_db_app):
        """Large binary data storage is equivalent in both databases."""
        large_data = b"x" * 100_000  # 100KB of data

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(path="/cid/large", file_data=large_data)
                db.session.add(cid)
                db.session.commit()

                retrieved = CID.query.filter_by(path="/cid/large").first()
                results[name] = len(retrieved.file_data)

        assert results["memory"] == results["disk"] == 100_000


@pytest.mark.db_equivalence
class TestPageViewEquivalence:
    """Test PageView model behaves identically in both database modes."""

    def test_create_page_view_equivalence(self, memory_db_app, disk_db_app):
        """Creating a page view produces equivalent results."""
        view_data = {
            "path": "/test/page",
            "method": "GET",
            "user_agent": "TestAgent/1.0",
            "ip_address": "192.168.1.1",
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                view = PageView(**view_data)
                db.session.add(view)
                db.session.commit()
                results[name] = {
                    "path": view.path,
                    "method": view.method,
                    "user_agent": view.user_agent,
                    "ip_address": view.ip_address,
                }

        assert results["memory"] == results["disk"]

    def test_page_view_aggregation_equivalence(self, memory_db_app, disk_db_app):
        """Aggregation queries produce equivalent results."""
        views = [
            {"path": "/page1", "method": "GET"},
            {"path": "/page1", "method": "GET"},
            {"path": "/page2", "method": "POST"},
            {"path": "/page1", "method": "GET"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for v in views:
                    db.session.add(PageView(**v))
                db.session.commit()

                counts = (
                    db.session.query(PageView.path, func.count(PageView.id))  # pylint: disable=not-callable
                    .group_by(PageView.path)
                    .order_by(PageView.path)
                    .all()
                )
                results[name] = dict(counts)

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestEntityInteractionEquivalence:
    """Test EntityInteraction model behaves identically in both database modes."""

    def test_create_interaction_equivalence(self, memory_db_app, disk_db_app):
        """Creating an entity interaction produces equivalent results."""
        interaction_data = {
            "entity_type": "Server",
            "entity_name": "test-server",
            "action": "create",
            "message": "Server created",
            "content": '{"key": "value"}',
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                interaction = EntityInteraction(**interaction_data)
                db.session.add(interaction)
                db.session.commit()
                results[name] = {
                    "entity_type": interaction.entity_type,
                    "entity_name": interaction.entity_name,
                    "action": interaction.action,
                    "message": interaction.message,
                    "content": interaction.content,
                }

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestServerInvocationEquivalence:
    """Test ServerInvocation model behaves identically in both database modes."""

    def test_create_invocation_equivalence(self, memory_db_app, disk_db_app):
        """Creating a server invocation produces equivalent results."""
        invocation_data = {
            "server_name": "test-server",
            "result_cid": "/cid/result123",
            "servers_cid": "/cid/servers456",
            "variables_cid": "/cid/vars789",
            "secrets_cid": "/cid/secrets012",
            "request_details_cid": "/cid/request345",
            "invocation_cid": "/cid/invoke678",
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                invocation = ServerInvocation(**invocation_data)
                db.session.add(invocation)
                db.session.commit()
                results[name] = {
                    "server_name": invocation.server_name,
                    "result_cid": invocation.result_cid,
                }

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestExportEquivalence:
    """Test Export model behaves identically in both database modes."""

    def test_create_export_equivalence(self, memory_db_app, disk_db_app):
        """Creating an export record produces equivalent results."""
        export_data = {"cid": "/cid/export123"}

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                export = Export(**export_data)
                db.session.add(export)
                db.session.commit()
                results[name] = {"cid": export.cid}

        assert results["memory"] == results["disk"]
