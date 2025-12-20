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
from db_access import get_cid_by_path
from models import Secret, Server, Variable

pytestmark = pytest.mark.integration


def test_servers_page_lists_saved_servers(
    client,
    integration_app,
):
    """The servers index page should list saved servers."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition=(
                'def main(city: str) -> str:\n    return f"Forecast for {city}"\n'
            ),
            definition_cid="bafyweatherdefinition",
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Servers" in page
    assert "weather" in page
    assert "View Full Definition" in page


def test_server_pages_show_implementation_language(
    client,
    integration_app,
):
    """View and edit pages should surface detected implementation language."""

    with integration_app.app_context():
        server = Server(
            name="script-server",
            definition=("#!/usr/bin/env bash\necho 'hello'\n"),
        )
        db.session.add(server)
        db.session.commit()

    view_response = client.get("/servers/script-server")
    assert view_response.status_code == 200
    view_page = view_response.get_data(as_text=True)
    assert "Implementation Language" in view_page
    assert "Bash" in view_page

    edit_response = client.get("/servers/script-server/edit")
    assert edit_response.status_code == 200
    edit_page = edit_response.get_data(as_text=True)
    assert "Implementation Language" in edit_page
    assert "Bash" in edit_page


def test_servers_page_includes_enabled_toggle(
    client,
    integration_app,
):
    """Each server row should display a toggle for its enabled state."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition="def main():\n    return 'ok'\n",
            enabled=False,
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'action="/servers/weather/enabled"' in page
    toggle_match = re.search(r'id="server-enabled-toggle-weather"[^>]*>', page)
    assert toggle_match is not None
    assert "checked" not in toggle_match.group(0)
    assert "server-enabled-label" in page


def test_server_enable_toggle_updates_state(
    client,
    integration_app,
):
    """Submitting the toggle form should persist the server enabled flag."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition="def main():\n    return 'ok'\n",
            enabled=False,
        )
        db.session.add(server)
        db.session.commit()

    response = client.post(
        "/servers/weather/enabled",
        data={"enabled": ["0", "1"]},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        server = Server.query.filter_by(name="weather").one()
        assert server.enabled is True

    response = client.post(
        "/servers/weather/enabled",
        data={"enabled": "0"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        server = Server.query.filter_by(name="weather").one()
        assert server.enabled is False


def test_servers_page_shows_referenced_variables_and_secrets(
    client,
    integration_app,
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
        )
        db.session.add(server)
        db.session.commit()

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
):
    """Auto main parameters should surface matching context links."""

    with integration_app.app_context():
        db.session.add(
            Variable(
                name="city",
                definition="return 'London'",
            )
        )
        db.session.add(
            Secret(
                name="api_token",
                definition="return 'secret'",
            )
        )
        db.session.add(
            Server(
                name="auto-main",
                definition=(
                    "def main(city, api_token):\n"
                    '    return {"output": city + api_token}\n'
                ),
            )
        )
        db.session.commit()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/variables/city" in page
    assert "/secrets/api_token" in page


def test_servers_page_shows_keyword_only_parameter_secrets(
    client,
    integration_app,
):
    """Servers with keyword-only secret parameters should list those secrets even if they don't exist."""

    with integration_app.app_context():
        db.session.add(
            Server(
                name="test-api-server",
                definition=(
                    "def main(message: str = 'Hello!', *, API_KEY: str, context=None):\n"
                    "    return {'output': f'{message} with {API_KEY}'}\n"
                ),
            )
        )
        db.session.commit()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show API_KEY as a potential secret parameter
    assert "API_KEY" in page


def test_servers_page_shows_lowercase_parameters_as_variables(
    client,
    integration_app,
):
    """Servers with lowercase main parameters should list them as variables even if they don't exist."""

    with integration_app.app_context():
        db.session.add(
            Server(
                name="test-var-server",
                definition=(
                    "def main(city, temperature):\n"
                    "    return {'output': f'{city}: {temperature}'}\n"
                ),
            )
        )
        db.session.commit()

    response = client.get("/servers")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show city and temperature as potential variables
    assert "city" in page
    assert "temperature" in page


def test_new_server_form_renders_in_single_user_mode(
    client,
):
    """The new-server form should render without explicit login helpers."""

    response = client.get("/servers/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Server" in page
    assert "Server Configuration" in page
    assert 'name="name"' in page
    assert 'name="definition"' in page


def test_new_server_form_includes_saved_templates(
    client,
    integration_app,
):
    """User-marked server templates should appear as reusable buttons."""

    with integration_app.app_context():
        # Create centralized templates variable with server template
        import json

        templates_config = {
            "aliases": {},
            "servers": {
                "templated-server": {
                    "name": "templated-server",
                    "definition": (
                        'def main(city: str) -> str:\n    return  {"output": city}\n'
                    ),
                }
            },
            "variables": {},
            "secrets": {},
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    response = client.get("/servers/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "data-server-template-id" in page
    assert "templated-server" in page


def test_new_server_form_includes_template_link(
    client,
    integration_app,
):
    """New server form should display a link to /variables/templates with status."""

    with integration_app.app_context():
        import json

        templates_config = {
            "aliases": {},
            "servers": {
                "server1": {
                    "name": "server1",
                    "definition": "test -> /test",
                }
            },
            "variables": {},
            "secrets": {},
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    response = client.get("/servers/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should have a link to /variables/templates?type=servers
    assert "/variables/templates" in page
    # Should show "1 template" for servers
    assert "1 template" in page


def test_server_detail_page_displays_server_information(
    client,
    integration_app,
):
    """Server detail page should render the saved definition and metadata."""

    with integration_app.app_context():
        server = Server(
            name="weather",
            definition=(
                'def main(city: str) -> str:\n    return f"Forecast for {city}"\n'
            ),
            definition_cid="bafyweatherdefinition",
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/servers/weather")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Server Definition" in page
    assert "weather" in page
    assert "Forecast for" in page
    assert "Definition Length:" in page
    assert "Run Test" in page


def test_server_config_tab_surfaces_named_values(
    client,
    integration_app,
):
    """The config tab should summarize pre-request named values."""

    with integration_app.app_context():
        db.session.add(
            Variable(
                name="city",
                definition="return 'London'",
            )
        )
        db.session.add(
            Secret(
                name="API_KEY",
                definition="return 'secret'",
            )
        )
        db.session.add(
            Server(
                name="configurable",
                definition=(
                    "def main(city, API_KEY, units='metric'):\n"
                    "    return {'output': city}\n"
                ),
            )
        )
        db.session.commit()

    client.set_cookie("city", "cookie-value")

    response = client.get("/servers/configurable")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Config" in page
    assert "Named value configuration" in page

    def _extract_status(name: str, source: str) -> str:
        pattern = rf'data-named-value-name="{name}" data-named-value-source="{source}">\s*<a[^>]*>([^<]+)'
        match = re.search(pattern, page, re.DOTALL)
        assert match, f"Missing status for {name} from {source}"
        return match.group(1).strip()

    assert _extract_status("city", "cookies") == "Defined"
    assert _extract_status("city", "variables") == "Overridden"
    assert _extract_status("API_KEY", "secrets") == "Defined"
    assert _extract_status("units", "variables") == "None"


def test_edit_server_updates_definition_snapshots(
    client,
    integration_app,
):
    """Editing a server should refresh definition CIDs for subsequent pages."""

    with integration_app.app_context():
        original_definition = (
            'def main(city: str) -> str:\n    return f"Response for {city}"\n'
        )
        original_cid = save_server_definition_as_cid(
            original_definition,
        )
        server = Server(
            name="weather",
            definition=original_definition,
            definition_cid=original_cid,
        )
        db.session.add(server)
        db.session.commit()

        initial_snapshot_cid = store_server_definitions_cid()

    updated_definition = (
        'def main(city: str) -> str:\n    return f"Updated forecast for {city}"\n'
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
            name="forecast",
        ).first()
        assert updated_server is not None
        assert updated_server.definition == updated_definition

        expected_definition_cid = format_cid(
            generate_cid(updated_definition.encode("utf-8"))
        )
        assert updated_server.definition_cid == expected_definition_cid

        definition_record = get_cid_by_path(f"/{expected_definition_cid}")
        assert definition_record is not None
        assert definition_record.file_data.decode("utf-8") == updated_definition

        expected_snapshot_json = generate_all_server_definitions_json()
        expected_snapshot_cid = format_cid(
            generate_cid(expected_snapshot_json.encode("utf-8"))
        )

        assert expected_snapshot_cid != initial_snapshot_cid

        snapshot_record = get_cid_by_path(f"/{expected_snapshot_cid}")
        assert snapshot_record is not None
        assert snapshot_record.file_data.decode("utf-8") == expected_snapshot_json

    page_response = client.get("/servers")
    assert page_response.status_code == 200

    page = page_response.get_data(as_text=True)
    assert "/servers/forecast" in page
    assert "/servers/weather" not in page
    assert expected_snapshot_cid in page
    assert initial_snapshot_cid not in page
