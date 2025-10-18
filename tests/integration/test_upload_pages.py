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
