"""Integration tests for the source browser page."""
from __future__ import annotations

import pytest

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
