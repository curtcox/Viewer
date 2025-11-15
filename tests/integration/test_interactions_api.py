"""Integration tests for the interactions API."""

from __future__ import annotations

import os

import pytest

from app import create_app
from database import db
from db_access import get_recent_entity_interactions

pytestmark = pytest.mark.integration


@pytest.fixture()
def integration_app():
    """Return a Flask app configured for integration testing."""

    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("SESSION_SECRET", "test-secret-key")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(integration_app):
    """Return a test client bound to the integration app."""

    return integration_app.test_client()


def test_interaction_endpoint_records_history(client, integration_app):
    """The interactions API should persist requests and return updated history."""

    payload = {
        "entity_type": "server",
        "entity_name": "demo-server",
        "action": "ai",
        "message": "format response",
        "content": "print('hello world')",
    }

    response = client.post("/api/interactions", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None
    assert data.get("interaction") is not None
    assert data["interaction"]["action"] == "ai"
    assert data["interaction"]["message"] == payload["message"]
    assert data["interaction"]["content"] == payload["content"]
    assert data.get("interactions")
    assert any(item.get("action") == "ai" for item in data["interactions"])

    with integration_app.app_context():
        history = get_recent_entity_interactions(
            "default-user",
            payload["entity_type"],
            payload["entity_name"],
            limit=1,
        )

    assert history, "The integration endpoint should create a database record."
    record = history[0]
    assert record.action == payload["action"]
    assert record.message == payload["message"]
    assert record.content == payload["content"]
