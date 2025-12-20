import pytest
import textwrap
from database import db
from models import Server

pytestmark = pytest.mark.integration


def _store_server(app, name: str, definition: str) -> None:
    """Persist a server definition."""
    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        existing = Server.query.filter_by(name=name).first()
        if existing:
            existing.definition = normalized
        else:
            db.session.add(Server(name=name, definition=normalized, enabled=True))
        db.session.commit()


def test_jq_availability(client, integration_app):
    """Verify jq is installed and functional."""
    _store_server(
        integration_app,
        "check_jq",
        """#!/bin/bash
        echo "PATH: $PATH"
        which jq 2>&1
        jq --version 2>&1
        echo '{"a": 1}' | jq .a 2>&1
        """,
    )

    _store_server(
        integration_app,
        "dummy",
        """
        def main():
            return {"output": "dummy", "content_type": "text/plain"}
        """,
    )

    response = client.get("/check_jq/dummy", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert "jq" in body, "jq command seems missing or failed"
    assert "1" in body


def test_tools_availability(client, integration_app):
    """Verify awk, sed, grep are available."""
    _store_server(
        integration_app,
        "check_tools",
        """#!/bin/bash
        which awk 2>&1
        which sed 2>&1
        which grep 2>&1
        """,
    )

    _store_server(
        integration_app,
        "dummy",
        """
        def main():
            return {"output": "dummy", "content_type": "text/plain"}
        """,
    )

    response = client.get("/check_tools/dummy", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert "awk" in body
    assert "sed" in body
    assert "grep" in body
