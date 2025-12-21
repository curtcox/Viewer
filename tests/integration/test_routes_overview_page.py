"""Integration tests for the routes overview page."""

from __future__ import annotations

import pytest

from alias_definition import format_primary_alias_line
from database import db
from models import Alias, Server

pytestmark = pytest.mark.integration


def test_routes_overview_lists_user_routes(
    client,
    integration_app,
):
    """The overview should include built-in, alias, and server entries."""

    with integration_app.app_context():
        db.session.add(
            Alias(
                name="docs",
                definition=format_primary_alias_line(
                    "literal",
                    None,
                    "/docs",
                    alias_name="docs",
                ),
            )
        )
        db.session.add(
            Server(
                name="toolbox",
                definition="return {'output': 'ok', 'content_type': 'text/plain'}",
            )
        )
        db.session.commit()

    response = client.get("/routes")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Routes Overview" in page
    assert "Alias: docs" in page
    assert "Server: toolbox" in page
    assert "Built-in route source" in page

    assert 'href="/docs"' in page
    assert 'href="/toolbox"' in page
    assert 'href="/aliases"' in page
