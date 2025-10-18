"""Integration coverage for upload-related pages."""
from __future__ import annotations

import pytest

from database import db
from models import CID

pytestmark = pytest.mark.integration


def test_uploads_page_displays_user_uploads(
    client,
    integration_app,
    login_default_user,
):
    """The uploads list should show manual uploads created by the user."""

    manual_cid_value = "bafyuploadcidexample"

    with integration_app.app_context():
        upload = CID(
            path=f"/{manual_cid_value}",
            file_data=b"Integration upload content",
            file_size=27,
            uploaded_by_user_id="default-user",
        )
        db.session.add(upload)
        db.session.commit()

    login_default_user()

    response = client.get("/uploads")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "My Uploads" in page
    assert "Total Files" in page
    assert f"#{manual_cid_value[:9]}..." in page


def test_upload_page_allows_user_to_choose_upload_method(
    client,
    login_default_user,
):
    """The upload form should render with options for file, text, and URL inputs."""

    login_default_user()

    response = client.get("/upload")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Upload Content" in page
    assert "Upload a file or paste text content" in page
    assert "upload_type_file" in page
    assert "upload_type_text" in page
    assert "upload_type_url" in page


def test_edit_cid_page_prefills_existing_content(
    client,
    integration_app,
    login_default_user,
):
    """Editing an existing CID should show the stored text content."""

    cid_value = "bafyeditcidexample"

    with integration_app.app_context():
        editable_cid = CID(
            path=f"/{cid_value}",
            file_data=b"Existing CID text content",
            file_size=24,
            uploaded_by_user_id="default-user",
        )
        db.session.add(editable_cid)
        db.session.commit()

    login_default_user()

    response = client.get(f"/edit/{cid_value}")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Edit CID Content" in page
    assert "Existing CID text content" in page
    assert "Optionally supply a new alias" in page


def test_edit_cid_choices_page_prompts_for_selection(
    client,
    integration_app,
    login_default_user,
):
    """When multiple CIDs match the prefix the choices page should render."""

    cid_prefix = "bafyshared"
    first_cid = f"{cid_prefix}alpha"
    second_cid = f"{cid_prefix}beta"

    with integration_app.app_context():
        db.session.add(
            CID(
                path=f"/{first_cid}",
                file_data=b"First matching content",
                file_size=22,
                uploaded_by_user_id="default-user",
            )
        )
        db.session.add(
            CID(
                path=f"/{second_cid}",
                file_data=b"Second matching content",
                file_size=23,
                uploaded_by_user_id="default-user",
            )
        )
        db.session.commit()

    login_default_user()

    response = client.get(f"/edit/{cid_prefix}")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Multiple Matches Found" in page
    assert f"href=\"/{first_cid}" in page
    assert f"href=\"/{second_cid}" in page
