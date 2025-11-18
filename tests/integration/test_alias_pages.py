"""Integration coverage for alias management pages."""
from __future__ import annotations

import re

import pytest

from alias_definition import format_primary_alias_line
from database import db
from models import Alias

pytestmark = pytest.mark.integration


def test_aliases_page_lists_saved_aliases(
    client,
    integration_app,
):
    """The aliases index should render saved aliases for the workspace."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs",
                alias_name="docs",
            ),
        )
        db.session.add(alias)
        db.session.commit()

    response = client.get("/aliases")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "docs" in page
    assert "/docs" in page


def test_aliases_page_includes_enabled_toggle(
    client,
    integration_app,
):
    """Each alias entry should expose a toggle reflecting its enabled state."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            enabled=False,
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs",
                alias_name="docs",
            ),
        )
        db.session.add(alias)
        db.session.commit()

    response = client.get("/aliases")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'action="/aliases/docs/enabled"' in page
    toggle_match = re.search(r'id="alias-enabled-toggle-docs"[^>]*>', page)
    assert toggle_match is not None
    assert 'checked' not in toggle_match.group(0)
    assert 'alias-enabled-label' in page


def test_alias_enable_toggle_updates_state(
    client,
    integration_app,
):
    """Submitting the toggle form should persist the new enabled state."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            enabled=False,
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs",
                alias_name="docs",
            ),
        )
        db.session.add(alias)
        db.session.commit()

    response = client.post(
        "/aliases/docs/enabled",
        data={"enabled": ["0", "1"]},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        alias = Alias.query.filter_by(name="docs").one()
        assert alias.enabled is True

    response = client.post(
        "/aliases/docs/enabled",
        data={"enabled": "0"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with integration_app.app_context():
        alias = Alias.query.filter_by(name="docs").one()
        assert alias.enabled is False


def test_new_alias_form_renders_in_single_user_mode(
    client,
):
    """The new-alias form should render without explicit login helpers."""

    response = client.get("/aliases/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Create New Alias" in page
    assert "name=\"name\"" in page
    assert "name=\"definition\"" in page
    assert "pattern -&gt; /target" in page


def test_alias_detail_page_displays_alias_information(
    client,
    integration_app,
):
    """Viewing an alias should show its saved details."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs",
                alias_name="docs",
            ),
        )
        db.session.add(alias)
        db.session.commit()

    response = client.get("/aliases/docs")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Alias Details" in page
    assert "<code>docs</code>" in page
    assert "<code>/docs</code>" in page


def test_new_alias_form_includes_template_options(
    client,
    integration_app,
):
    """Template aliases should surface as reusable buttons on the new form."""

    with integration_app.app_context():
        # Create centralized templates variable with alias template
        import json
        from models import Variable

        templates_config = {
            "aliases": {
                "template-source": {
                    "name": "template-source",
                    "definition": format_primary_alias_line(
                        'literal',
                        '/template-source',
                        '/target',
                        alias_name='template-source',
                    ),
                }
            },
            "servers": {},
            "variables": {},
            "secrets": {}
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    response = client.get("/aliases/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "data-alias-template-id" in page
    assert "template-source" in page


def test_new_alias_form_includes_template_link(
    client,
    integration_app,
):
    """New alias form should display a link to /variables/templates with status."""

    with integration_app.app_context():
        # Create centralized templates variable with alias template
        import json
        from models import Variable

        templates_config = {
            "aliases": {
                "template1": {
                    "name": "template1",
                    "definition": "test -> /test",
                },
                "template2": {
                    "name": "template2",
                    "definition": "test2 -> /test2",
                }
            },
            "servers": {},
            "variables": {},
            "secrets": {}
        }

        templates_var = Variable(
            name="templates",
            definition=json.dumps(templates_config),
        )
        db.session.add(templates_var)
        db.session.commit()

    response = client.get("/aliases/new")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should have a link to /variables/templates?type=aliases
    assert "/variables/templates" in page
    # Should show "2 templates" for aliases
    assert "2 templates" in page or "2 template" in page
