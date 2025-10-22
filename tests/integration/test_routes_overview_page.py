"""Integration tests for the routes overview page."""
from __future__ import annotations

import pytest

from database import db
from identity import ensure_default_user
from alias_definition import format_primary_alias_line
from models import Alias, Server

pytestmark = pytest.mark.integration


def test_routes_overview_lists_user_routes(
    client,
    integration_app,
    login_default_user,
):
    """The overview should include built-in, alias, and server entries."""

    with integration_app.app_context():
        user = ensure_default_user()
        db.session.add(
            Alias(
                name="docs",
                user_id=user.id,
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
                user_id=user.id,
            )
        )
        db.session.commit()

    login_default_user()

    response = client.get("/routes")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Routes Overview" in page
    assert "Alias: docs" in page
    assert "Server: toolbox" in page
    assert "Built-in route source" in page
