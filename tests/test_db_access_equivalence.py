# tests/test_db_access_equivalence.py
"""Equivalence tests for db_access module operations."""

import pytest

from database import db
from models import Alias, CID, PageView, Server
from cid import CID as ValidatedCID


@pytest.mark.db_equivalence
class TestGenericCrudEquivalence:
    """Test GenericEntityRepository behaves identically in both database modes."""

    def test_get_all_equivalence(self, memory_db_app, disk_db_app):
        """get_all() produces equivalent results."""
        from db_access.generic_crud import GenericEntityRepository

        servers = [
            {"name": "server-c", "definition": "c"},
            {"name": "server-a", "definition": "a"},
            {"name": "server-b", "definition": "b"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

                repo = GenericEntityRepository(Server)
                all_servers = repo.get_all()
                results[name] = [s.name for s in all_servers]

        assert results["memory"] == results["disk"]
        # Should be sorted by name
        assert results["memory"] == ["server-a", "server-b", "server-c"]

    def test_get_by_name_equivalence(self, memory_db_app, disk_db_app):
        """get_by_name() produces equivalent results."""
        from db_access.generic_crud import GenericEntityRepository

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="find-me", definition="found"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                server = repo.get_by_name("find-me")
                results[name] = server.definition if server else None

        assert results["memory"] == results["disk"] == "found"

    def test_count_equivalence(self, memory_db_app, disk_db_app):
        """count() produces equivalent results."""
        from db_access.generic_crud import GenericEntityRepository

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                for i in range(5):
                    db.session.add(Server(name=f"server-{i}", definition=f"def-{i}"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                results[name] = repo.count()

        assert results["memory"] == results["disk"] == 5

    def test_exists_equivalence(self, memory_db_app, disk_db_app):
        """exists() produces equivalent results."""
        from db_access.generic_crud import GenericEntityRepository

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="exists-test", definition="yes"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                results[name] = {
                    "exists": repo.exists("exists-test"),
                    "not_exists": repo.exists("nonexistent"),
                }

        assert results["memory"] == results["disk"]
        assert results["memory"]["exists"] is True
        assert results["memory"]["not_exists"] is False


@pytest.mark.db_equivalence
class TestServersModuleEquivalence:
    """Test servers.py module behaves identically in both database modes."""

    def test_get_servers_equivalence(self, memory_db_app, disk_db_app):
        """get_servers() produces equivalent results."""
        from db_access.servers import get_servers

        servers = [
            {"name": "srv-2", "definition": "def2", "enabled": True},
            {"name": "srv-1", "definition": "def1", "enabled": False},
            {"name": "srv-3", "definition": "def3", "enabled": True},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

                result = get_servers()
                results[name] = [(s.name, s.enabled) for s in result]

        assert results["memory"] == results["disk"]

    def test_get_server_by_name_equivalence(self, memory_db_app, disk_db_app):
        """get_server_by_name() produces equivalent results."""
        from db_access.servers import get_server_by_name

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="target", definition="target-def"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = get_server_by_name("target")
                results[name] = server.definition if server else None

        assert results["memory"] == results["disk"] == "target-def"


@pytest.mark.db_equivalence
class TestAliasesModuleEquivalence:
    """Test aliases.py module behaves identically in both database modes."""

    def test_get_aliases_equivalence(self, memory_db_app, disk_db_app):
        """get_aliases() produces equivalent results."""
        from db_access.aliases import get_aliases

        aliases = [
            {"name": "alias-b", "definition": "/b"},
            {"name": "alias-a", "definition": "/a"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for a in aliases:
                    db.session.add(Alias(**a))
                db.session.commit()

                result = get_aliases()
                results[name] = [(a.name, a.definition) for a in result]

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestCIDsModuleEquivalence:
    """Test cids.py module behaves identically in both database modes."""

    def test_create_cid_record_equivalence(self, memory_db_app, disk_db_app):
        """create_cid_record() produces equivalent results."""
        from db_access.cids import create_cid_record

        file_content = b"test data"
        cid_value = ValidatedCID.from_bytes(file_content).value

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                record = create_cid_record(cid_value, file_content)
                results[name] = {
                    "path": record.path,
                    "data_len": len(record.file_data),
                }

        assert results["memory"] == results["disk"]

    def test_find_cids_by_prefix_equivalence(self, memory_db_app, disk_db_app):
        """find_cids_by_prefix() produces equivalent results."""
        from db_access.cids import find_cids_by_prefix

        cids = [
            {"path": "/cid/abc123", "file_data": b"1"},
            {"path": "/cid/abc456", "file_data": b"2"},
            {"path": "/cid/xyz789", "file_data": b"3"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for c in cids:
                    db.session.add(CID(**c))
                db.session.commit()

                found = find_cids_by_prefix("/cid/abc")
                results[name] = sorted([c.path for c in found])

        assert results["memory"] == results["disk"]
        assert len(results["memory"]) == 2


@pytest.mark.db_equivalence
class TestPageViewsModuleEquivalence:
    """Test page_views.py module behaves identically in both database modes."""

    def test_save_page_view_equivalence(self, memory_db_app, disk_db_app):
        """save_page_view() produces equivalent results."""
        from db_access.page_views import save_page_view

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                view = save_page_view(
                    PageView(
                        path="/test",
                        method="GET",
                        user_agent="Test",
                        ip_address="127.0.0.1",
                    )
                )
                results[name] = {"path": view.path, "method": view.method}

        assert results["memory"] == results["disk"]

    def test_count_page_views_equivalence(self, memory_db_app, disk_db_app):
        """count_page_views() produces equivalent results."""
        from db_access.page_views import count_page_views

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                for i in range(10):
                    db.session.add(PageView(path=f"/page{i}", method="GET"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                results[name] = count_page_views()

        assert results["memory"] == results["disk"] == 10


@pytest.mark.db_equivalence
class TestInteractionsModuleEquivalence:
    """Test interactions.py module behaves identically in both database modes."""

    def test_record_entity_interaction_equivalence(self, memory_db_app, disk_db_app):
        """record_entity_interaction() produces equivalent results."""
        from db_access.interactions import (
            EntityInteractionRequest,
            record_entity_interaction,
        )

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                interaction = record_entity_interaction(
                    EntityInteractionRequest(
                        entity_type="Server",
                        entity_name="test-server",
                        action="create",
                        message="Created server",
                        content="definition",
                    )
                )
                results[name] = {
                    "entity_type": interaction.entity_type,
                    "action": interaction.action,
                }

        assert results["memory"] == results["disk"]


@pytest.mark.db_equivalence
class TestInvocationsModuleEquivalence:
    """Test invocations.py module behaves identically in both database modes."""

    def test_create_server_invocation_equivalence(self, memory_db_app, disk_db_app):
        """create_server_invocation() produces equivalent results."""
        from db_access.invocations import create_server_invocation

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                invocation = create_server_invocation(
                    server_name="test-server",
                    result_cid="/cid/result",
                    servers_cid="/cid/servers",
                    variables_cid="/cid/vars",
                    secrets_cid="/cid/secrets",
                    request_details_cid="/cid/request",
                    invocation_cid="/cid/invocation",
                )
                results[name] = {
                    "server_name": invocation.server_name,
                    "result_cid": invocation.result_cid,
                }

        assert results["memory"] == results["disk"]
