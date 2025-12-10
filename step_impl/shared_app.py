"""Utilities for sharing a single Flask app across Gauge step modules."""

from __future__ import annotations

from typing import Optional, Tuple

from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from boot_cid_importer import import_boot_cid
from cid_directory_loader import load_cids_from_directory
from identity import ensure_default_resources
from main import get_default_boot_cid

_app: Optional[Flask] = None
_client: Optional[FlaskClient] = None


def _initialise_app() -> Tuple[Flask, FlaskClient]:
    """Create the shared Flask app and client if they do not already exist."""

    # pylint: disable=global-statement
    # Gauge maintains global state for step implementations across the suite.
    global _app, _client

    if _app is None or _client is None:
        app = create_app({"TESTING": True, "LOAD_CIDS_IN_TESTS": True})
        with app.app_context():
            load_cids_from_directory(app)
            default_boot_cid = get_default_boot_cid()

            if default_boot_cid:
                success, error = import_boot_cid(app, default_boot_cid)
                if not success:
                    raise RuntimeError(
                        f"Failed to import default boot CID {default_boot_cid}: {error}"
                    )

            ensure_default_resources()
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


__all__ = ["get_shared_app", "get_shared_client"]
