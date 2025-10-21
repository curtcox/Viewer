"""Integration coverage for variable management pages."""
from __future__ import annotations

import pytest

from cid_presenter import format_cid
from cid_utils import (
    generate_all_variable_definitions_json,
    generate_cid,
    store_variable_definitions_cid,
)
from database import db
from models import CID, Variable

pytestmark = pytest.mark.integration


def test_variables_page_lists_user_variables(
    client,
    integration_app,
    login_default_user,
):
    """The variables index page should list the user's variables."""

    with integration_app.app_context():
        variable = Variable(
            name="API_URL",
            definition="https://example.com/api",
            user_id="default-user",
        )
        db.session.add(variable)
        db.session.commit()

    login_default_user()

    response = client.get("/variables")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "My Variables" in page
    assert "API_URL" in page
    assert "https://example.com/api" in page


def test_variable_detail_page_displays_variable_information(
    client,
    integration_app,
    login_default_user,
):
    """The variable detail page should render the variable metadata."""

    with integration_app.app_context():
        variable = Variable(
            name="API_TOKEN",
            definition="super-secret-token",
            user_id="default-user",
        )
        db.session.add(variable)
        db.session.commit()

    login_default_user()

    response = client.get("/variables/API_TOKEN")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Variable Definition" in page
    assert "super-secret-token" in page
    assert "Variable Information" in page


def test_new_variable_form_renders_for_authenticated_user(
    client,
    login_default_user,
):
    """The new-variable form should render for logged-in users."""

    login_default_user()

    response = client.get("/variables/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Variable" in page
    assert "Variable Configuration" in page
    assert 'name="name"' in page
    assert 'name="definition"' in page


def test_edit_variable_form_displays_existing_variable_details(
    client,
    integration_app,
    login_default_user,
):
    """Editing a variable should prefill the form with its saved details."""

    with integration_app.app_context():
        variable = Variable(
            name="API_TOKEN",
            definition="super-secret-token",
            user_id="default-user",
        )
        db.session.add(variable)
        db.session.commit()

    login_default_user()

    response = client.get("/variables/API_TOKEN/edit")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Edit Variable" in page
    assert "<code>API_TOKEN</code>" in page
    assert "super-secret-token" in page


def test_edit_variable_updates_definition_snapshot(
    client,
    integration_app,
    login_default_user,
):
    """Variable edits should persist new definitions for subsequent page loads."""

    with integration_app.app_context():
        variable = Variable(
            name="city",
            definition="return 'Paris'",
            user_id="default-user",
        )
        db.session.add(variable)
        db.session.commit()

        initial_snapshot_cid = store_variable_definitions_cid("default-user")

    login_default_user()

    updated_definition = "return 'Berlin'"

    response = client.post(
        "/variables/city/edit",
        data={
            "name": "region",
            "definition": updated_definition,
            "change_message": "rename variable",
            "submit": "Save Variable",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/variables/region")

    with integration_app.app_context():
        updated_variable = Variable.query.filter_by(
            user_id="default-user",
            name="region",
        ).first()
        assert updated_variable is not None
        assert updated_variable.definition == updated_definition

        expected_snapshot_json = generate_all_variable_definitions_json("default-user")
        expected_snapshot_cid = format_cid(
            generate_cid(expected_snapshot_json.encode("utf-8"))
        )

        assert expected_snapshot_cid != initial_snapshot_cid

        snapshot_record = CID.query.filter_by(
            path=f"/{expected_snapshot_cid}",
        ).first()
        assert snapshot_record is not None
        assert snapshot_record.file_data.decode("utf-8") == expected_snapshot_json

    page_response = client.get("/variables")
    assert page_response.status_code == 200

    page = page_response.get_data(as_text=True)
    assert "/variables/region" in page
    assert "/variables/city" not in page
    assert expected_snapshot_cid in page
    assert initial_snapshot_cid not in page
