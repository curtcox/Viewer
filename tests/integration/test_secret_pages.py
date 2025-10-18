"""Integration coverage for secret management pages."""
from __future__ import annotations

import pytest

from database import db
from models import Secret

pytestmark = pytest.mark.integration


def test_new_secret_form_renders_for_authenticated_user(
    client,
    login_default_user,
):
    """The new-secret form should render when the user is logged in."""

    login_default_user()

    response = client.get("/secrets/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Secret" in page
    assert "Secret Configuration" in page
    assert "name=\"name\"" in page
    assert "name=\"definition\"" in page


def test_edit_secret_form_displays_existing_secret(
    client,
    integration_app,
    login_default_user,
):
    """Editing a secret should show the saved metadata and preview."""

    with integration_app.app_context():
        secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
            user_id="default-user",
        )
        db.session.add(secret)
        db.session.commit()

    login_default_user()

    response = client.get("/secrets/production-api-key/edit")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Edit Secret" in page
    assert "production-api-key" in page
    assert "super-secret-value" in page
    assert "Current Secret Name" in page
    assert "<code>production-api-key</code>" in page


def test_secret_detail_page_displays_secret_information(
    client,
    integration_app,
    login_default_user,
):
    """Viewing a secret should show its metadata and controls."""

    with integration_app.app_context():
        secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
            user_id="default-user",
        )
        db.session.add(secret)
        db.session.commit()

    login_default_user()

    response = client.get("/secrets/production-api-key")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Secret Definition" in page
    assert "Secret Information" in page
    assert "production-api-key" in page
    assert "super-secret-value" in page
    assert "Back to Secrets" in page
