"""Integration tests for the settings page."""
from __future__ import annotations

import pytest

from alias_definition import format_primary_alias_line
from database import db
from db_access import (
    count_user_aliases,
    count_user_secrets,
    count_user_servers,
    count_user_variables,
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
    login_default_user,
):
    """Settings page should list saved resources and expose direct access links."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            user_id="default-user",
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
            "alias": count_user_aliases("default-user"),
            "server": count_user_servers("default-user"),
            "variable": count_user_variables("default-user"),
            "secret": count_user_secrets("default-user"),
        }
        examples = {
            "alias": get_first_alias_name("default-user"),
            "server": get_first_server_name("default-user"),
            "variable": get_first_variable_name("default-user"),
            "secret": get_first_secret_name("default-user"),
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

    if examples["alias"]:
        assert f'href="/{examples["alias"]}"' in page
    if examples["server"]:
        assert f'href="/servers/{examples["server"]}"' in page
    if examples["variable"]:
        assert f'href="/variables/{examples["variable"]}"' in page
    if examples["secret"]:
        assert f'href="/secrets/{examples["secret"]}"' in page
