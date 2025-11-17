"""Integration tests for the profile page."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_profile_page_links_to_workspace(
    client,
):
    """Authenticated users should see the workspace shortcut on the profile page."""

    response = client.get("/profile")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Account Profile" in page
    assert "href=\"/uploads\"" in page
    assert "Open Workspace" in page
