"""Integration coverage for server management pages."""
from __future__ import annotations

import pytest

from database import db
from models import Server


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
