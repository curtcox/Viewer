from __future__ import annotations

import pytest

from cid_presenter import format_cid
from database import db
from models import CID, Server

pytestmark = pytest.mark.integration


def test_route_details_for_builtin_index(client, login_default_user):
    """The route explorer should describe built-in Flask routes."""

    login_default_user()

    response = client.get("/")
    assert response.status_code == 200

    detail_response = client.get("/routes/")
    assert detail_response.status_code == 200

    page = detail_response.get_data(as_text=True)
    assert "Route Explorer" in page
    assert "Handled by Flask endpoint main.index" in page
    assert 'badge text-bg-primary me-2">200' in page


def test_route_details_for_alias_redirect(client, login_default_user):
    """Alias routes should surface their target path and redirect."""

    login_default_user()

    alias_response = client.get("/css/darkmode", follow_redirects=False)
    assert alias_response.status_code == 302
    target = alias_response.headers.get("Location")
    assert target

    detail_response = client.get("/routes/css/darkmode")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "Alias" in page
    assert "CSS" in page
    assert target in page


def test_route_details_for_server_execution(client, integration_app, login_default_user):
    """Server-backed routes should report the server definition."""

    with integration_app.app_context():
        db.session.add(
            Server(
                name="demo", 
                definition=(
                    "def main():\n"
                    "    return {'output': 'demo output', 'content_type': 'text/plain'}\n"
                ),
                user_id="default-user",
            )
        )
        db.session.commit()

    login_default_user()

    server_response = client.get("/demo", follow_redirects=False)
    assert server_response.status_code == 302
    redirect_target = server_response.headers.get("Location")
    assert redirect_target and redirect_target.startswith("/")

    detail_response = client.get("/routes/demo")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "Server" in page
    assert "demo" in page
    assert "Executes server code" in page


def test_route_details_for_direct_cid(client, integration_app, login_default_user):
    """CID paths should display CID helper markup."""

    cid_value = format_cid("abcdef123456")

    with integration_app.app_context():
        db.session.add(
            CID(
                path=f"/{cid_value}",
                file_data=b"hello world",
                uploaded_by_user_id="default-user",
            )
        )
        db.session.commit()

    login_default_user()

    cid_response = client.get(f"/{cid_value}")
    assert cid_response.status_code == 200

    detail_response = client.get(f"/routes/{cid_value}")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "CID" in page
    assert "cid-display" in page
    assert cid_value in page
