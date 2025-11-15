"""Utilities for sharing a single Flask app across Gauge step modules."""

from __future__ import annotations

from typing import Optional, Tuple

from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from identity import ensure_default_user

_app: Optional[Flask] = None
_client: Optional[FlaskClient] = None


def _initialise_app() -> Tuple[Flask, FlaskClient]:
    """Create the shared Flask app and client if they do not already exist."""

    # pylint: disable=global-statement
    # Gauge maintains global state for step implementations across the suite.
    global _app, _client

    if _app is None or _client is None:
        app = create_app({"TESTING": True})
        client = app.test_client()
        _app = app
        _client = client

    # ``_app`` and ``_client`` are guaranteed to be initialised here.
    return _app, _client  # type: ignore[misc]


def get_shared_app() -> Flask:
    """Return the shared Flask application instance."""

    app, _ = _initialise_app()
    return app


def get_shared_client() -> FlaskClient:
    """Return the shared Flask test client instance."""

    _, client = _initialise_app()
    return client


def login_default_user() -> str:
    """Attach the default user session to the shared Flask client."""

    app, client = _initialise_app()

    with app.app_context():
        user = ensure_default_user()

    with client.session_transaction() as session:
        session["_fresh"] = True

    return user.id


__all__ = ["get_shared_app", "get_shared_client", "login_default_user"]
