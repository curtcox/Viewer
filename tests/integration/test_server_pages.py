"""Integration coverage for server management pages."""
from __future__ import annotations

import re

import pytest

from cid_presenter import format_cid
from cid_utils import (
    generate_all_server_definitions_json,
    generate_cid,
    save_server_definition_as_cid,
    store_server_definitions_cid,
)
from database import db
from models import CID, Secret, Server, Variable

pytestmark = pytest.mark.integration


def test_servers_page_lists_user_servers(
    client,
    integration_app,
    login_default_user,
):
    """The servers index page should list servers belonging to the user."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition=(
                "def main(city: str) -> str:\n"
                "    return f\"Forecast for {city}\"\n"
            ),
            definition_cid="bafyweatherdefinition",
            user_id="default-user",
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "My Servers" in page
    assert "weather" in page
    assert "View Full Definition" in page


def test_servers_page_includes_enabled_toggle(
    client,
    integration_app,
    login_default_user,
):
    """Each server row should display a toggle for its enabled state."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition="def main():\n    return 'ok'\n",
            user_id="default-user",
            enabled=False,
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'action="/servers/weather/enabled"' in page
    toggle_match = re.search(r'id="server-enabled-toggle-weather"[^>]*>', page)
    assert toggle_match is not None
    assert 'checked' not in toggle_match.group(0)
    assert 'server-enabled-label' in page


def test_server_enable_toggle_updates_state(
    client,
    integration_app,
    login_default_user,
):
    """Submitting the toggle form should persist the server enabled flag."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition="def main():\n    return 'ok'\n",
            user_id="default-user",
            enabled=False,
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.post(
        "/servers/weather/enabled",
        data={"enabled": ["0", "1"]},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        server = Server.query.filter_by(user_id="default-user", name="weather").one()
        assert server.enabled is True

    response = client.post(
        "/servers/weather/enabled",
        data={"enabled": "0"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        server = Server.query.filter_by(user_id="default-user", name="weather").one()
        assert server.enabled is False


def test_servers_page_shows_referenced_variables_and_secrets(
    client,
    integration_app,
    login_default_user,
):
    """Server reference badges should mirror context usage in definitions."""

    with integration_app.app_context():
        server = Server(
            name="reference-links",
            definition=(
                "def main(context):\n"
                "    city = context['variables']['city']\n"
                "    duplicate_city = context['variables'].get('city')\n"
                "    units = context['variables'].get('units', 'metric')\n"
                "    token = context['secrets']['api_token']\n"
                "    fallback = context['secrets'].get('api_token')\n"
                "    return f'{city} {units} {token or fallback}'\n"
            ),
            definition_cid="bafyreferencelinks",
            user_id="default-user",
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/variables/city" in page
    assert page.count("/variables/city") == 1
    assert "/variables/units" in page
    assert page.count("/variables/units") == 1
    assert "/secrets/api_token" in page
    assert page.count("/secrets/api_token") == 1


def test_servers_page_links_auto_main_context_matches(
    client,
    integration_app,
    login_default_user,
):
    """Auto main parameters should surface matching context links."""

    with integration_app.app_context():
        db.session.add(
            Variable(
                name="city",
                definition="return 'London'",
                user_id="default-user",
            )
        )
        db.session.add(
            Secret(
                name="api_token",
                definition="return 'secret'",
                user_id="default-user",
            )
        )
        db.session.add(
            Server(
                name="auto-main",
                definition=(
                    "def main(city, api_token):\n"
                    "    return {\"output\": city + api_token}\n"
                ),
                user_id="default-user",
            )
        )
        db.session.commit()

    login_default_user()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/variables/city" in page
    assert "/secrets/api_token" in page


def test_new_server_form_renders_for_authenticated_user(
    client,
    login_default_user,
):
    """The new-server form should render the creation UI when logged in."""

    login_default_user()

    response = client.get("/servers/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Server" in page
    assert "Server Configuration" in page
    assert "name=\"name\"" in page
    assert "name=\"definition\"" in page


def test_new_server_form_includes_saved_templates(
    client,
    integration_app,
    login_default_user,
):
    """User-marked server templates should appear as reusable buttons."""

    with integration_app.app_context():
        server = Server(
            name="templated-server",
            definition="def main():\n    return {'output': 'ok'}\n",
            user_id="default-user",
            template=True,
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.get("/servers/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "data-server-template-id" in page
    assert "templated-server" in page
    assert "name=\"template\"" in page


def test_server_detail_page_displays_server_information(
    client,
    integration_app,
    login_default_user,
):
    """Server detail page should render the saved definition and metadata."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition=(
                "def main(city: str) -> str:\n"
                "    return f\"Forecast for {city}\"\n"
            ),
            definition_cid="bafyweatherdefinition",
            user_id="default-user",
        )
        db.session.add(server)
        db.session.commit()

    login_default_user()

    response = client.get("/servers/weather")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Server Definition" in page
    assert "weather" in page
    assert "Forecast for" in page
    assert "Definition Length:" in page
    assert "Run Test" in page


def test_edit_server_updates_definition_snapshots(
    client,
    integration_app,
    login_default_user,
):
    """Editing a server should refresh definition CIDs for subsequent pages."""

    with integration_app.app_context():
        original_definition = (
            "def main(city: str) -> str:\n"
            "    return f\"Response for {city}\"\n"
        )
        original_cid = save_server_definition_as_cid(
            original_definition,
            "default-user",
        )
        server = Server(
            name="weather",
            definition=original_definition,
            definition_cid=original_cid,
            user_id="default-user",
        )
        db.session.add(server)
        db.session.commit()

        initial_snapshot_cid = store_server_definitions_cid("default-user")

    login_default_user()

    updated_definition = (
        "def main(city: str) -> str:\n"
        "    return f\"Updated forecast for {city}\"\n"
    )

    response = client.post(
        "/servers/weather/edit",
        data={
            "name": "forecast",
            "definition": updated_definition,
            "change_message": "rename server",
            "submit": "Rename to forecast",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/servers/forecast")

    with integration_app.app_context():
        updated_server = Server.query.filter_by(
            user_id="default-user",
            name="forecast",
        ).first()
        assert updated_server is not None
        assert updated_server.definition == updated_definition

        expected_definition_cid = format_cid(
            generate_cid(updated_definition.encode("utf-8"))
        )
        assert updated_server.definition_cid == expected_definition_cid

        definition_record = CID.query.filter_by(
            path=f"/{expected_definition_cid}",
        ).first()
        assert definition_record is not None
        assert definition_record.file_data.decode("utf-8") == updated_definition

        expected_snapshot_json = generate_all_server_definitions_json("default-user")
        expected_snapshot_cid = format_cid(
            generate_cid(expected_snapshot_json.encode("utf-8"))
        )

        assert expected_snapshot_cid != initial_snapshot_cid

        snapshot_record = CID.query.filter_by(
            path=f"/{expected_snapshot_cid}",
        ).first()
        assert snapshot_record is not None
        assert snapshot_record.file_data.decode("utf-8") == expected_snapshot_json

    page_response = client.get("/servers")
    assert page_response.status_code == 200

    page = page_response.get_data(as_text=True)
    assert "/servers/forecast" in page
    assert "/servers/weather" not in page
    assert expected_snapshot_cid in page
    assert initial_snapshot_cid not in page
