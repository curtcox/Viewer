"""Integration tests for the source browser and instance pages."""

from __future__ import annotations

import pytest

from database import db
from models import Variable
from routes.source import get_current_commit_sha

pytestmark = pytest.mark.integration


def test_source_browser_lists_directories(
    client,
):
    """The source browser should render a directory listing for the project root."""

    response = client.get("/source")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Source Browser" in page
    assert ">templates/</a>" in page


def test_source_browser_displays_file_content(
    client,
):
    """Viewing an individual file should render its contents."""

    response = client.get("/source/README.md")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Source Browser" in page
    assert "Viewer is a Flask based web application" in page


def test_source_browser_links_to_instance_overview(
    client,
):
    """The source browser should link to the database instance overview."""

    response = client.get("/source")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/source/instance" in page
    assert "Database Tables" in page


def test_source_browser_displays_running_commit_link(
    client,
):
    """The source browser should display a link to the running commit."""

    response = client.get("/source")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    repository_root = client.application.root_path
    sha = get_current_commit_sha(repository_root)

    if not sha:
        pytest.skip("The running commit SHA could not be determined")

    expected_url = f"https://github.com/curtcox/Viewer/tree/{sha}"
    assert expected_url in page
    assert sha[:7] in page


def test_source_instance_lists_tables(
    client,
    integration_app,
):
    """The instance page should enumerate database tables and their columns."""

    response = client.get("/source/instance")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/source/instance/variable" in page
    assert "name" in page


def test_source_instance_table_view_displays_rows(
    client,
    integration_app,
):
    """Viewing a specific table should render its rows in an HTML table."""

    with integration_app.app_context():
        db.session.add(Variable(name="example", definition="value"))
        db.session.commit()

    response = client.get("/source/instance/variable")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Table: <code>variable</code>" in page
    assert "example" in page
    assert "value" in page
