"""Integration coverage for alias management pages."""
from __future__ import annotations

import os

import pytest

from app import create_app
from database import db
from identity import ensure_default_user
from models import Alias

pytestmark = pytest.mark.integration


@pytest.fixture()
def integration_app():
    """Return a Flask app configured for integration testing."""

    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("SESSION_SECRET", "integration-secret-key")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        ensure_default_user()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(integration_app):
    """Return a test client bound to the integration app."""

    return integration_app.test_client()


def _login_default_user(client):
    """Authenticate the default user for the request session."""

    with client.session_transaction() as session:
        session["_user_id"] = "default-user"
        session["_fresh"] = True


def test_aliases_page_lists_user_aliases(client, integration_app):
    """The aliases index should render saved aliases for the default user."""

    with integration_app.app_context():
        alias = Alias(
            name="docs",
            target_path="/docs",
            user_id="default-user",
        )
        db.session.add(alias)
        db.session.commit()

    _login_default_user(client)

    response = client.get("/aliases")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "docs" in page
    assert "/docs" in page
