# tests/test_routes_equivalence.py
"""API route equivalence tests for memory vs disk databases."""

from __future__ import annotations

from typing import Iterable

import pytest

from database import db
from models import Alias, Server


def _populate_servers(app, servers: Iterable[dict]) -> None:
    """Insert server records into the provided Flask app context."""

    with app.app_context():
        for data in servers:
            db.session.add(Server(**data))
        db.session.commit()


def _populate_aliases(app, aliases: Iterable[dict]) -> None:
    """Insert alias records into the provided Flask app context."""

    with app.app_context():
        for data in aliases:
            db.session.add(Alias(**data))
        db.session.commit()


@pytest.mark.db_equivalence
class TestServerRoutesEquivalence:
    """Ensure server routes behave the same in both database modes."""

    def test_list_servers_equivalence(self, memory_client, disk_client):
        servers = [
            {"name": "srv-b", "definition": "def-b", "enabled": False},
            {"name": "srv-a", "definition": "def-a", "enabled": True},
        ]

        for client in (memory_client, disk_client):
            _populate_servers(client.application, servers)

        memory_response = memory_client.get(
            "/servers", headers={"Accept": "application/json"}
        )
        disk_response = disk_client.get(
            "/servers", headers={"Accept": "application/json"}
        )

        assert memory_response.status_code == disk_response.status_code == 200

        memory_payload = sorted(
            [{"name": row["name"], "enabled": row.get("enabled", True)} for row in memory_response.get_json()],
            key=lambda row: row["name"],
        )
        disk_payload = sorted(
            [{"name": row["name"], "enabled": row.get("enabled", True)} for row in disk_response.get_json()],
            key=lambda row: row["name"],
        )

        assert memory_payload == disk_payload

    def test_toggle_server_enabled_equivalence(self, memory_client, disk_client):
        for client in (memory_client, disk_client):
            _populate_servers(
                client.application,
                [
                    {
                        "name": "toggle-me",
                        "definition": "return 'ok'",
                        "enabled": False,
                    }
                ],
            )

            response = client.post("/servers/toggle-me/enabled", data={"enabled": "1"})
            assert response.status_code == 302

            with client.application.app_context():
                server = Server.query.filter_by(name="toggle-me").first()
                assert server is not None
                assert server.enabled is True


@pytest.mark.db_equivalence
class TestAliasRoutesEquivalence:
    """Ensure alias routes behave the same in both database modes."""

    def test_list_aliases_equivalence(self, memory_client, disk_client):
        aliases = [
            {"name": "alias-b", "definition": "literal -> /b", "enabled": True},
            {"name": "alias-a", "definition": "literal -> /a", "enabled": False},
        ]

        for client in (memory_client, disk_client):
            _populate_aliases(client.application, aliases)

        memory_response = memory_client.get(
            "/aliases", headers={"Accept": "application/json"}
        )
        disk_response = disk_client.get("/aliases", headers={"Accept": "application/json"})

        assert memory_response.status_code == disk_response.status_code == 200

        memory_payload = sorted(
            [
                {
                    "name": row["name"],
                    "enabled": row.get("enabled", True),
                    "target_path": row.get("target_path"),
                }
                for row in memory_response.get_json()
            ],
            key=lambda row: row["name"],
        )
        disk_payload = sorted(
            [
                {
                    "name": row["name"],
                    "enabled": row.get("enabled", True),
                    "target_path": row.get("target_path"),
                }
                for row in disk_response.get_json()
            ],
            key=lambda row: row["name"],
        )

        assert memory_payload == disk_payload

    def test_toggle_alias_enabled_equivalence(self, memory_client, disk_client):
        alias_definition = "literal -> /servers/example"

        for client in (memory_client, disk_client):
            _populate_aliases(
                client.application,
                [
                    {
                        "name": "toggle-alias",
                        "definition": alias_definition,
                        "enabled": False,
                    }
                ],
            )

            response = client.post(
                "/aliases/toggle-alias/enabled", data={"enabled": "1"}
            )
            assert response.status_code == 302

            with client.application.app_context():
                alias = Alias.query.filter_by(name="toggle-alias").first()
                assert alias is not None
                assert alias.enabled is True
