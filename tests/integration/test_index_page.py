"""Integration tests for the index (homepage) view."""
from __future__ import annotations

import pytest

from alias_definition import format_primary_alias_line
from cid_utils import generate_cid
from database import db
from models import CID, Alias, Secret, Server, Variable

pytestmark = pytest.mark.integration


def test_index_page_displays_cross_reference_dashboard(
    client,
    integration_app,
):
    """Authenticated users should see saved entities on the cross-reference dashboard."""

    with integration_app.app_context():
        cid_value = generate_cid(b"Integration cross-reference sample")
        cid_record = CID(
            path=f"/{cid_value}",
            file_data=b"Integration cross-reference sample",
        )
        alias = Alias(
            name="sample-alias",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/servers/sample-server",
                alias_name="sample-alias",
            ),
        )
        server = Server(
            name="sample-server",
            definition=(
                "def main(request):\n"
                "    return \"Visit /aliases/sample-alias\"\n"
            ),
            definition_cid=f"/{cid_value}",
        )

        db.session.add_all([cid_record, alias, server])
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Workspace Cross Reference" in page
    assert 'href="/aliases/sample-alias"' in page
    assert 'href="/servers/sample-server"' in page
    assert "crossref-reference" in page


def test_viewer_menu_lists_user_entities(
    client,
    integration_app,
):
    """The unified Viewer menu should surface key workspace resources."""

    with integration_app.app_context():
        alias = Alias(
            name="menu-alias",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/servers/menu-server",
                alias_name="menu-alias",
            ),
        )
        server = Server(
            name="menu-server",
            definition="def main(request):\n    return 'ok'\n",
        )
        variable = Variable(
            name="menu-variable",
            definition="value = 'menu'",
        )
        secret = Secret(
            name="menu-secret",
            definition="token=123",
        )

        db.session.add_all([alias, server, variable, secret])
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'data-viewer-menu' in page
    assert 'href="/aliases/menu-alias"' in page
    assert 'href="/servers/menu-server"' in page
    assert 'href="/variables/menu-variable"' in page
    assert 'href="/secrets/menu-secret"' in page
    assert 'href="/routes"' in page
    assert 'href="/source"' in page
