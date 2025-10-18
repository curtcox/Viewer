"""Integration coverage for server detail pages."""
from __future__ import annotations

import pytest

from database import db
from models import Server


pytestmark = pytest.mark.integration


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
