"""Integration coverage for secret management pages."""
from __future__ import annotations

import pytest

from cid_presenter import format_cid
from cid_utils import (
    generate_all_secret_definitions_json,
    generate_cid,
    store_secret_definitions_cid,
)
from database import db
from models import CID, Secret

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


def test_secrets_list_page_displays_user_secrets(
    client,
    integration_app,
    login_default_user,
):
    """The secrets overview should list saved secrets for the user."""

    with integration_app.app_context():
        first_secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
            user_id="default-user",
        )
        second_secret = Secret(
            name="staging-api-key",
            definition="staging-secret-value",
            user_id="default-user",
        )
        db.session.add_all([first_secret, second_secret])
        db.session.commit()

    login_default_user()

    response = client.get("/secrets")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "My Secrets" in page
    assert "production-api-key" in page
    assert "staging-api-key" in page
    assert "Create New Secret" in page


def test_edit_secret_updates_definition_snapshot(
    client,
    integration_app,
    login_default_user,
):
    """Secret edits should update cached definition snapshots immediately."""

    with integration_app.app_context():
        secret = Secret(
            name="api-token",
            definition="return 'old-secret'",
            user_id="default-user",
        )
        db.session.add(secret)
        db.session.commit()

        initial_snapshot_cid = store_secret_definitions_cid("default-user")

    login_default_user()

    updated_definition = "return 'new-secret'"

    response = client.post(
        "/secrets/api-token/edit",
        data={
            "name": "service-token",
            "definition": updated_definition,
            "change_message": "rename secret",
            "submit": "Save Secret",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secrets/service-token")

    with integration_app.app_context():
        updated_secret = Secret.query.filter_by(
            user_id="default-user",
            name="service-token",
        ).first()
        assert updated_secret is not None
        assert updated_secret.definition == updated_definition

        expected_snapshot_json = generate_all_secret_definitions_json("default-user")
        expected_snapshot_cid = format_cid(
            generate_cid(expected_snapshot_json.encode("utf-8"))
        )

        assert expected_snapshot_cid != initial_snapshot_cid

        snapshot_record = CID.query.filter_by(
            path=f"/{expected_snapshot_cid}",
        ).first()
        assert snapshot_record is not None
        assert snapshot_record.file_data.decode("utf-8") == expected_snapshot_json

    page_response = client.get("/secrets")
    assert page_response.status_code == 200

    page = page_response.get_data(as_text=True)
    assert "/secrets/service-token" in page
    assert "/secrets/api-token" not in page
    assert expected_snapshot_cid in page
    assert initial_snapshot_cid not in page
