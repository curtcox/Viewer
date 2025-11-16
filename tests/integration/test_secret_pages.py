"""Integration coverage for secret management pages."""
from __future__ import annotations

import json

import re

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


def test_new_secret_form_includes_templates(
    client,
    integration_app,
    login_default_user,
):
    """Secrets flagged as templates should appear on the new form."""

    with integration_app.app_context():
        # Create centralized templates variable with secret template
        from models import Variable

        templates_config = {
            "aliases": {},
            "servers": {},
            "variables": {},
            "secrets": {
                "templated-secret": {
                    "name": "templated-secret",
                    "definition": "return 'secret'",
                }
            }
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    login_default_user()

    response = client.get("/secrets/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "data-secret-template-id" in page
    assert "templated-secret" in page


def test_new_secret_form_includes_template_link(
    client,
    integration_app,
    login_default_user,
):
    """New secret form should display a link to /variables/templates with status."""

    with integration_app.app_context():
        from models import Variable

        templates_config = {
            "aliases": {},
            "servers": {},
            "variables": {},
            "secrets": {
                "secret1": {
                    "name": "secret1",
                    "definition": "secret-value-1",
                }
            }
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    login_default_user()

    response = client.get("/secrets/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should have a link to /variables/templates?type=secrets
    assert "/variables/templates" in page
    # Should show "1 template" for secrets
    assert "1 template" in page


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


def test_secrets_list_page_displays_saved_secrets(
    client,
    integration_app,
    login_default_user,
):
    """The secrets overview should list saved secrets for the user."""

    with integration_app.app_context():
        first_secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
        )
        second_secret = Secret(
            name="staging-api-key",
            definition="staging-secret-value",
        )
        db.session.add_all([first_secret, second_secret])
        db.session.commit()

    login_default_user()

    response = client.get("/secrets")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Secrets" in page
    assert "production-api-key" in page
    assert "staging-api-key" in page
    assert "Create New Secret" in page


def test_secrets_page_includes_enabled_toggle(
    client,
    integration_app,
    login_default_user,
):
    """Each secret card should display an enabled toggle."""

    with integration_app.app_context():
        secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
            enabled=False,
        )
        db.session.add(secret)
        db.session.commit()

    login_default_user()

    response = client.get("/secrets")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'action="/secrets/production-api-key/enabled"' in page
    toggle_match = re.search(r'id="secret-enabled-toggle-production-api-key"[^>]*>', page)
    assert toggle_match is not None
    assert 'checked' not in toggle_match.group(0)
    assert 'secret-enabled-label' in page


def test_secret_enable_toggle_updates_state(
    client,
    integration_app,
    login_default_user,
):
    """Submitting the toggle form should persist the secret's enabled flag."""

    with integration_app.app_context():
        secret = Secret(
            name="production-api-key",
            definition="super-secret-value",
            enabled=False,
        )
        db.session.add(secret)
        db.session.commit()

    login_default_user()

    response = client.post(
        "/secrets/production-api-key/enabled",
        data={"enabled": ["0", "1"]},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        secret = Secret.query.filter_by(
            name="production-api-key",
        ).one()
        assert secret.enabled is True

    response = client.post(
        "/secrets/production-api-key/enabled",
        data={"enabled": "0"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        secret = Secret.query.filter_by(
            name="production-api-key",
        ).one()
        assert secret.enabled is False


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
        )
        db.session.add(secret)
        db.session.commit()

        initial_snapshot_cid = store_secret_definitions_cid()

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
            name="service-token",
        ).first()
        assert updated_secret is not None
        assert updated_secret.definition == updated_definition

        expected_snapshot_json = generate_all_secret_definitions_json()
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


def test_bulk_secret_editor_prefills_existing_secrets(
    client,
    integration_app,
    login_default_user,
):
    """The bulk editor should render the current secrets as JSON."""

    with integration_app.app_context():
        db.session.add(
            Secret(name="api_key", definition="super-secret")
        )
        db.session.add(
            Secret(name="db_password", definition="hunter2")
        )
        db.session.commit()

    login_default_user()

    response = client.get("/secrets/_/edit")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'api_key' in page
    assert 'super-secret' in page
    assert 'db_password' in page


def test_bulk_secret_editor_updates_and_deletes_secrets(
    client,
    integration_app,
    login_default_user,
):
    """Saving from the bulk editor should upsert provided secrets and remove omissions."""

    with integration_app.app_context():
        db.session.add(
            Secret(name="api_key", definition="super-secret")
        )
        db.session.add(
            Secret(name="db_password", definition="hunter2")
        )
        db.session.commit()

    login_default_user()

    payload = {"api_key": "rotate-me", "service_token": "abc123"}
    response = client.post(
        "/secrets/_/edit",
        data={
            "secrets_json": json.dumps(payload),
            "submit": "Save Secrets",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secrets")

    with integration_app.app_context():
        api_key = Secret.query.filter_by(name="api_key").one()
        service_token = Secret.query.filter_by(
            name="service_token"
        ).one()
        db_password = Secret.query.filter_by(
            name="db_password"
        ).first()

        assert api_key.definition == "rotate-me"
        assert service_token.definition == "abc123"
        assert service_token.enabled is True
        assert db_password is None


def test_bulk_secret_editor_invalid_json_displays_errors(
    client,
    integration_app,
    login_default_user,
):
    """Invalid JSON submissions should be rejected and show an error message."""

    with integration_app.app_context():
        db.session.add(
            Secret(name="api_key", definition="super-secret")
        )
        db.session.commit()

    login_default_user()

    response = client.post(
        "/secrets/_/edit",
        data={
            "secrets_json": '{"api_key": "super-secret"',
            "submit": "Save Secrets",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Invalid JSON" in page

    with integration_app.app_context():
        api_key = Secret.query.filter_by(name="api_key").one()
        assert api_key.definition == "super-secret"
