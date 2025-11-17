"""Integration coverage for upload-related pages."""
from __future__ import annotations

import pytest

from database import db
from models import CID

pytestmark = pytest.mark.integration


def test_uploads_page_displays_saved_uploads(
    client,
    integration_app,
    login_default_user,
):
    """The uploads list should show manual uploads created in the system."""

    manual_cid_value = "bafyuploadcidexample"

    with integration_app.app_context():
        upload = CID(
            path=f"/{manual_cid_value}",
            file_data=b"Integration upload content",
            file_size=27,
        )
        db.session.add(upload)
        db.session.commit()

    login_default_user()

    response = client.get("/uploads")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Uploads" in page
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
            )
        )
        db.session.add(
            CID(
                path=f"/{second_cid}",
                file_data=b"Second matching content",
                file_size=23,
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


def test_upload_page_displays_templates_when_configured(
    client,
    integration_app,
    login_default_user,
):
    """Upload page should display template buttons when upload templates are defined."""
    import json
    from models import Variable

    templates_config = {
        'aliases': {},
        'servers': {},
        'variables': {},
        'secrets': {},
        'uploads': {
            'hello_world': {
                'name': 'Hello World',
                'content': 'Hello, World!\n'
            },
            'json_example': {
                'name': 'JSON Example',
                'content': '{\n  "key": "value"\n}'
            }
        }
    }

    with integration_app.app_context():
        templates_var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    login_default_user()

    response = client.get("/upload")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Start from a Template" in page
    assert "Hello World" in page
    assert "JSON Example" in page
    assert 'data-upload-template-id="hello_world"' in page
    assert 'data-upload-template-id="json_example"' in page


def test_upload_page_shows_template_status_link(
    client,
    integration_app,
    login_default_user,
):
    """Upload page should show a link to the templates configuration page."""
    import json
    from models import Variable

    templates_config = {
        'aliases': {},
        'servers': {},
        'variables': {},
        'secrets': {},
        'uploads': {
            'test_template': {
                'name': 'Test Template',
                'content': 'Test content'
            }
        }
    }

    with integration_app.app_context():
        templates_var = Variable(
            name='templates',
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    login_default_user()

    response = client.get("/upload")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/variables/templates?type=uploads" in page
    assert "1 template" in page or "templates" in page


def test_upload_page_no_templates_shown_when_none_configured(
    client,
    login_default_user,
):
    """Upload page should not show template section when no templates are configured."""

    login_default_user()

    response = client.get("/upload")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should not show the template selection UI
    assert "Start from a Template" not in page or 'data-upload-template-id' not in page
