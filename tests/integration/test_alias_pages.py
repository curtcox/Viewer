"""Integration coverage for alias management pages."""
from __future__ import annotations

import pytest

from database import db
from models import Alias

pytestmark = pytest.mark.integration


def test_aliases_page_lists_user_aliases(
    client,
    integration_app,
    login_default_user,
):
    """The aliases index should render saved aliases for the default user."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            target_path="/docs",
            user_id="default-user",
        )
        db.session.add(alias)
        db.session.commit()

    login_default_user()

    response = client.get("/aliases")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "docs" in page
    assert "/docs" in page


def test_new_alias_form_renders_for_authenticated_user(
    client,
    login_default_user,
):
    """The new-alias form should render when the user is logged in."""

    login_default_user()

    response = client.get("/aliases/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Alias" in page
    assert "name=\"name\"" in page
    assert "name=\"target_path\"" in page
