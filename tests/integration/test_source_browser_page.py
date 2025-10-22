"""Integration tests for the source browser and instance pages."""
from __future__ import annotations

import pytest

from database import db
from models import Variable

pytestmark = pytest.mark.integration


def test_source_browser_lists_directories(
    client,
    login_default_user,
):
    """The source browser should render a directory listing for the project root."""

    login_default_user()

    response = client.get("/source")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Source Browser" in page
    assert ">templates/</a>" in page


def test_source_browser_displays_file_content(
    client,
    login_default_user,
):
    """Viewing an individual file should render its contents."""

    login_default_user()

    response = client.get("/source/README.md")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Source Browser" in page
    assert "Viewer is a Flask based web application" in page


def test_source_browser_links_to_instance_overview(
    client,
    login_default_user,
):
    """The source browser should link to the database instance overview."""

    login_default_user()

    response = client.get("/source")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/source/instance" in page
    assert "Database Tables" in page


def test_source_instance_lists_tables(
    client,
    integration_app,
    login_default_user,
):
    """The instance page should enumerate database tables and their columns."""

    login_default_user()

    response = client.get("/source/instance")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/source/instance/variable" in page
    assert "name" in page


def test_source_instance_table_view_displays_rows(
    client,
    integration_app,
    login_default_user,
):
    """Viewing a specific table should render its rows in an HTML table."""

    login_default_user()

    with integration_app.app_context():
        db.session.add(
            Variable(name="example", definition="value", user_id="default-user")
        )
        db.session.commit()

    response = client.get("/source/instance/variable")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Table: <code>variable</code>" in page
    assert "example" in page
    assert "value" in page
