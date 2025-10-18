"""Shared integration test fixtures."""
from __future__ import annotations

import os

import pytest

from app import create_app
from database import db
from identity import ensure_default_user


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


@pytest.fixture()
def login_default_user(client):
    """Authenticate the default user within the test client session."""

    def _login():
        with client.session_transaction() as session:
            session["_user_id"] = "default-user"
            session["_fresh"] = True

    return _login
