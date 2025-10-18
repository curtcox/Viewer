"""Gauge steps for exercising the import and export workflow."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from flask.testing import FlaskClient
from getgauge.python import after_scenario, before_scenario, step

from app import create_app
from cid_presenter import cid_path
from database import db
from identity import ensure_default_user
from models import CID, Server


_scenario_state: dict[str, Any] = {}
_created_apps: list[Any] = []
_created_db_paths: list[Path] = []


def _login_default_user(client: FlaskClient) -> None:
    """Attach the default user session to the provided test client."""
    with client.session_transaction() as session:
        session["_user_id"] = "default-user"
        session["_fresh"] = True


def _create_isolated_site(label: str) -> tuple[Any, FlaskClient]:
    """Return a Flask app and client backed by an isolated database."""
    fd, db_path_str = tempfile.mkstemp(prefix=f"gauge-{label}-", suffix=".sqlite3")
    os.close(fd)
    db_path = Path(db_path_str)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
        }
    )

    client = app.test_client()
    _login_default_user(client)

    _created_apps.append(app)
    _created_db_paths.append(db_path)

    return app, client


@before_scenario()
def reset_scenario_state() -> None:
    """Clear per-scenario state before each scenario begins."""
    _scenario_state.clear()


@after_scenario()
def cleanup_created_sites() -> None:
    """Dispose of database connections and temporary files created in a scenario."""
    for app in _created_apps:
        with app.app_context():
            db.session.remove()
    _created_apps.clear()

    for db_path in _created_db_paths:
        if db_path.exists():
            db_path.unlink()
    _created_db_paths.clear()


@step('Given an origin site with a server named "{}" returning "{}"')
def given_origin_site_with_server(server_name: str, server_message: str) -> None:
    """Create an origin site that hosts the provided server implementation."""
    origin_app, origin_client = _create_isolated_site("origin")

    server_definition = (
        "return {\"output\": \""
        + server_message
        + "\", \"content_type\": \"text/plain\"}"
    )

    with origin_app.app_context():
        user = ensure_default_user()
        db.session.add(
            Server(name=server_name, definition=server_definition, user_id=user.id)
        )
        db.session.commit()

    _scenario_state.update(
        {
            "origin_app": origin_app,
            "origin_client": origin_client,
            "server_name": server_name,
            "server_message": server_message,
            "server_definition": server_definition,
        }
    )


@step("And I export servers and their CID map from the origin site")
def and_i_export_servers_from_origin() -> None:
    """Run an export that includes servers and the CID map, capturing the payload."""
    origin_app = _scenario_state.get("origin_app")
    origin_client = _scenario_state.get("origin_client")
    assert origin_app is not None and origin_client is not None, "Origin site is not configured."

    export_response = origin_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "submit": True,
        },
    )
    assert (
        export_response.status_code == 200
    ), f"Expected export to succeed, received {export_response.status_code}."

    with origin_app.app_context():
        export_record = next(
            (
                record
                for record in CID.query.order_by(CID.id.desc()).all()
                if b'"servers"' in record.file_data
            ),
            None,
        )
        assert export_record is not None, "Expected a stored export payload."
        export_payload = export_record.file_data.decode("utf-8")
        parsed_payload = json.loads(export_payload)

    _scenario_state.update(
        {
            "export_payload": export_payload,
            "parsed_export": parsed_payload,
        }
    )


@step("When I import the exported data into a fresh destination site")
def when_i_import_exported_data_into_destination() -> None:
    """Import the captured payload into a new destination site."""
    export_payload = _scenario_state.get("export_payload")
    assert export_payload, "No export payload is available to import."

    destination_app, destination_client = _create_isolated_site("destination")

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
    assert (
        import_response.status_code == 302
    ), f"Expected import to redirect on success, received {import_response.status_code}."

    _scenario_state.update(
        {
            "destination_app": destination_app,
            "destination_client": destination_client,
        }
    )


@step('Then the destination site should have a server named "{}"')
def then_destination_has_server(server_name: str) -> None:
    """Verify the imported site now owns a server with the expected name and content."""
    destination_app = _scenario_state.get("destination_app")
    parsed_export = _scenario_state.get("parsed_export")
    server_definition = _scenario_state.get("server_definition")
    assert destination_app is not None, "Destination site is not available."
    assert parsed_export is not None, "Export metadata is missing."

    with destination_app.app_context():
        user = ensure_default_user()
        imported_server = Server.query.filter_by(name=server_name, user_id=user.id).first()
        assert imported_server is not None, "Imported server was not found."
        assert (
            imported_server.definition == server_definition
        ), "Imported server definition does not match the origin definition."

        servers_section = parsed_export.get("servers", [])
        exported_entry = next(
            (entry for entry in servers_section if entry.get("name") == server_name),
            None,
        )
        assert exported_entry is not None, "Export payload did not include the server entry."
        expected_cid = exported_entry.get("definition_cid")
        assert expected_cid, "Exported server did not record a definition CID."
        assert (
            imported_server.definition_cid == expected_cid
        ), "Imported server definition CID does not match export metadata."

        cid_record = CID.query.filter_by(path=cid_path(expected_cid)).first()
        assert cid_record is not None, "Definition CID file was not stored on import."
        assert (
            cid_record.file_data.decode("utf-8") == server_definition
        ), "Imported CID content does not match the server definition."

    _scenario_state["destination_server_name"] = server_name


@step('And executing "{}" on the destination site should return "{}"')
def and_executing_destination_route_returns_message(route_path: str, expected_message: str) -> None:
    """Execute the imported server and confirm the expected response content."""
    destination_client = _scenario_state.get("destination_client")
    assert destination_client is not None, "Destination client is not configured."

    execution_response = destination_client.get(route_path, follow_redirects=False)
    assert (
        execution_response.status_code == 302
    ), f"Expected execution redirect, received {execution_response.status_code}."

    redirect_location = execution_response.headers.get("Location")
    assert redirect_location, "Execution redirect did not specify a location."

    content_response = destination_client.get(redirect_location)
    assert content_response.status_code == 200, "CID content request failed."
    assert (
        expected_message in content_response.get_data(as_text=True)
    ), "Imported server did not return the expected output."
