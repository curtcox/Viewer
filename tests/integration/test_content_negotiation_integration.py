"""Integration tests for content negotiation across documented endpoints."""
from __future__ import annotations

import json

import pytest


@pytest.mark.integration
def test_aliases_endpoint_supports_json_extension(client, login_default_user) -> None:
    login_default_user()
    response = client.get("/aliases.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert payload is not None
    assert payload.get("content_type") == "text/html"
    assert "Aliases" in payload.get("content", "")


@pytest.mark.integration
def test_aliases_endpoint_honors_plain_text_accept_header(client, login_default_user) -> None:
    login_default_user()
    response = client.get("/aliases", headers={"Accept": "text/plain"})

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert "Aliases" in body


@pytest.mark.integration
def test_interactions_endpoint_supports_xml_extension(client, login_default_user) -> None:
    login_default_user()
    payload = {
        "entity_type": "server",
        "entity_name": "example-server",
        "action": "ai",
        "message": "Trigger negotiation test",
        "content": "print('hello world')",
    }

    response = client.post("/api/interactions.xml", data=json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    body = response.get_data(as_text=True)
    assert "<response>" in body
    assert "Trigger negotiation test" in body
