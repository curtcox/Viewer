"""Integration tests for the settings page."""
from __future__ import annotations

import pytest

from database import db
from models import Alias, Secret, Server, Variable


pytestmark = pytest.mark.integration


def test_settings_page_displays_resource_counts_and_links(
    client,
    integration_app,
    login_default_user,
):
    """Settings page should list saved resources and expose direct access links."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            target_path="/docs-target",
            user_id="default-user",
            match_type="literal",
            ignore_case=False,
        )
        server = Server(
            name="engine",
            definition="print(\"ok\")",
            user_id="default-user",
        )
        variable = Variable(
            name="app-config",
            definition="value = 1",
            user_id="default-user",
        )
        secret = Secret(
            name="api-key",
            definition="secret-value",
            user_id="default-user",
        )
        db.session.add_all([alias, server, variable, secret])
        db.session.commit()

        counts = {
            "alias": Alias.query.filter_by(user_id="default-user").count(),
            "server": Server.query.filter_by(user_id="default-user").count(),
            "variable": Variable.query.filter_by(user_id="default-user").count(),
            "secret": Secret.query.filter_by(user_id="default-user").count(),
        }
        examples = {
            "alias": (
                Alias.query.filter_by(user_id="default-user")
                .order_by(Alias.name.asc())
                .first()
            ),
            "server": (
                Server.query.filter_by(user_id="default-user")
                .order_by(Server.name.asc())
                .first()
            ),
            "variable": (
                Variable.query.filter_by(user_id="default-user")
                .order_by(Variable.name.asc())
                .first()
            ),
            "secret": (
                Secret.query.filter_by(user_id="default-user")
                .order_by(Secret.name.asc())
                .first()
            ),
        }

    login_default_user()

    response = client.get("/settings")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Settings" in page

    alias_label = "alias" if counts["alias"] == 1 else "aliases"
    server_label = "server" if counts["server"] == 1 else "servers"
    variable_label = "variable" if counts["variable"] == 1 else "variables"
    secret_label = "secret" if counts["secret"] == 1 else "secrets"

    assert f"{counts['alias']} {alias_label}" in page
    assert f"{counts['server']} {server_label}" in page
    assert f"{counts['variable']} {variable_label}" in page
    assert f"{counts['secret']} {secret_label}" in page

    alias_example = examples["alias"].name if examples["alias"] else None
    server_example = examples["server"].name if examples["server"] else None
    variable_example = examples["variable"].name if examples["variable"] else None
    secret_example = examples["secret"].name if examples["secret"] else None

    if alias_example:
        assert f'href="/{alias_example}"' in page
    if server_example:
        assert f'href="/servers/{server_example}"' in page
    if variable_example:
        assert f'href="/variables/{variable_example}"' in page
    if secret_example:
        assert f'href="/secrets/{secret_example}"' in page
