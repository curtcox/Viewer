"""Tests for the routes overview API endpoint."""

from flask.testing import FlaskClient


def test_routes_overview_api_returns_json(memory_client: FlaskClient):
    """The API should respond with JSON describing available routes."""

    response = memory_client.get("/api/routes")

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")

    payload = response.get_json()
    assert payload is not None
    assert "routes" in payload

    routes = payload["routes"]
    assert isinstance(routes, list)
    # There should always be at least one built-in route (e.g., the index page).
    assert any(entry.get("path") == "/" for entry in routes)

    sample = routes[0]
    assert {"category", "path", "name", "definition_label", "definition_url", "is_duplicate"} <= sample.keys()
