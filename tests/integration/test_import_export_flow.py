"""Integration tests verifying import/export data transfer between instances."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Callable

import pytest
from flask import Flask

from app import create_app
from cid_presenter import cid_path
from database import db
from identity import ensure_default_user
from models import CID, Server

pytestmark = pytest.mark.integration


@pytest.fixture()
def app_factory(tmp_path) -> Callable[[], Flask]:
    """Return a factory that constructs isolated Flask apps for integration tests."""

    # Ensure required environment variables exist for application setup.
    os.environ.setdefault("SESSION_SECRET", "test-secret-key")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

    created_apps: list[tuple[Flask, Path]] = []

    def _create_app():
        db_path = tmp_path / f"viewer-integration-{len(created_apps)}.sqlite"
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                "WTF_CSRF_ENABLED": False,
            }
        )

        with app.app_context():
            db.create_all()
            ensure_default_user()

        created_apps.append((app, db_path))
        return app

    yield _create_app

    for app, db_path in created_apps:
        with app.app_context():
            db.session.remove()
            db.drop_all()
        if db_path.exists():
            db_path.unlink()


def _login_default_user(client) -> None:
    """Attach the default user to the provided test client session."""

    with client.session_transaction() as session:
        session["_user_id"] = "default-user"
        session["_fresh"] = True


def _load_section(payload: dict[str, Any], key: str):
    section_cid = payload.get(key)
    if section_cid is None:
        return None
    cid_values = payload.get("cid_values", {})
    entry = cid_values.get(section_cid)
    assert entry is not None, f"Expected CID {section_cid} for section {key}"
    encoding = (entry.get("encoding") or "utf-8").lower()
    value = entry.get("value")
    assert isinstance(value, str), f"CID {section_cid} for {key} must include string content"
    if encoding == "base64":
        content_bytes = base64.b64decode(value.encode("ascii"))
    else:
        content_bytes = value.encode("utf-8")
    return json.loads(content_bytes.decode("utf-8"))


def test_user_can_transport_server_between_sites(app_factory) -> None:
    """Exporting from one instance and importing into another should preserve servers."""

    origin_app = app_factory()
    server_name = "shared-tool"
    server_definition = 'return {"output": "Hello from origin", "content_type": "text/plain"}'

    with origin_app.app_context():
        user = ensure_default_user()
        db.session.add(
            Server(name=server_name, definition=server_definition, user_id=user.id)
        )
        db.session.commit()

    origin_client = origin_app.test_client()
    _login_default_user(origin_client)

    export_response = origin_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "submit": True,
        },
    )
    assert export_response.status_code == 200

    with origin_app.app_context():
        export_record = next(
            (
                record
                for record in CID.query.order_by(CID.id.desc()).all()
                if b'"servers"' in record.file_data
            ),
            None,
        )
        assert export_record is not None, "Expected an export payload stored as a CID."
        export_payload = export_record.file_data.decode("utf-8")
        parsed_payload = json.loads(export_payload)

    destination_app = app_factory()
    destination_client = destination_app.test_client()
    _login_default_user(destination_client)

    import_response = destination_client.post(
        "/import",
        data={
            "import_source": "text",
            "import_text": export_payload,
            "include_servers": "y",
            "process_cid_map": "y",
            "submit": True,
        },
        follow_redirects=False,
    )
    assert import_response.status_code == 302

    with destination_app.app_context():
        user = ensure_default_user()
        imported_server = Server.query.filter_by(name=server_name, user_id=user.id).first()
        assert imported_server is not None, "Server should exist after import."
        assert imported_server.definition == server_definition

        servers_section = _load_section(parsed_payload, "servers") or []
        exported_entry = next(
            (entry for entry in servers_section if entry.get("name") == server_name),
            None,
        )
        assert exported_entry is not None, "Export payload should include the created server."

        expected_cid = exported_entry["definition_cid"]
        assert expected_cid in parsed_payload.get("cid_values", {})
        assert imported_server.definition_cid == expected_cid

        cid_record_path = cid_path(expected_cid)
        assert cid_record_path is not None
        cid_record = CID.query.filter_by(path=cid_record_path).first()
        assert cid_record is not None
        assert cid_record.file_data.decode("utf-8") == server_definition

    execution_response = destination_client.get(f"/{server_name}", follow_redirects=False)
    assert execution_response.status_code == 302

    redirect_location = execution_response.headers.get("Location")
    assert redirect_location, "Server execution should redirect to CID content."

    content_response = destination_client.get(redirect_location)
    assert content_response.status_code == 200
    assert "Hello from origin" in content_response.get_data(as_text=True)
