"""Integration tests for the settings page."""
from __future__ import annotations

import pytest

from alias_definition import format_primary_alias_line
from database import db
from db_access import (
    count_aliases,
    count_secrets,
    count_servers,
    count_variables,
    get_first_alias_name,
    get_first_secret_name,
    get_first_server_name,
    get_first_variable_name,
)
from models import Alias, Secret, Server, Variable

pytestmark = pytest.mark.integration


def test_settings_page_displays_resource_counts_and_links(
    client,
    integration_app,
):
    """Settings page should list saved resources and expose direct access links."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs-target",
                alias_name="docs",
            ),
        )
        server = Server(
            name="engine",
            definition="print(\"ok\")",
        )
        variable = Variable(
            name="app-config",
            definition="value = 1",
        )
        secret = Secret(
            name="api-key",
            definition="secret-value",
        )
        db.session.add_all([alias, server, variable, secret])
        db.session.commit()

        counts = {
            "alias": count_aliases(),
            "server": count_servers(),
            "variable": count_variables(),
            "secret": count_secrets(),
        }
        examples = {
            "alias": get_first_alias_name(),
            "server": get_first_server_name(),
            "variable": get_first_variable_name(),
            "secret": get_first_secret_name(),
        }

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

    if examples["alias"]:
        assert f'href="/{examples["alias"]}"' in page
    if examples["server"]:
        assert f'href="/servers/{examples["server"]}"' in page
    if examples["variable"]:
        assert f'href="/variables/{examples["variable"]}"' in page
    if examples["secret"]:
        assert f'href="/secrets/{examples["secret"]}"' in page
