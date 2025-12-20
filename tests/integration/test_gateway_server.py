"""Integration tests for gateway server functionality."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from database import db
from models import Server

pytestmark = pytest.mark.integration


def test_gateway_server_shows_examples_page(
    client,
    integration_app,
):
    """Gateway server without target_server should show examples page."""

    # Load gateway definition from template
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    # Request gateway without target_server
    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Gateway Server" in page
    assert "API Examples" in page
    assert "GitHub API" in page
    assert "OpenAI API" in page
    assert "Anthropic API" in page


def test_gateway_server_examples_have_proper_links(
    client,
    integration_app,
):
    """Gateway examples page should have clickable links to API servers."""

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # Check that examples have proper gateway links
    assert "/gateway?target_server=https://api.github.com" in page
    assert "/gateway?target_server=https://api.openai.com" in page
    assert "/gateway?target_server=https://api.anthropic.com" in page


@patch("requests.request")
def test_gateway_server_proxies_to_target(
    mock_request,
    client,
    integration_app,
):
    """Gateway should proxy requests to the target server."""

    # Mock the response from the target server
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b'{"message": "Hello from API", "status": "ok"}'
    mock_response.text = '{"message": "Hello from API", "status": "ok"}'
    mock_response.json.return_value = {"message": "Hello from API", "status": "ok"}
    mock_request.return_value = mock_response

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    # Make a request through the gateway
    response = client.get(
        "/gateway/test?target_server=https://api.example.com", follow_redirects=True
    )
    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # Should render as HTML
    assert response.content_type.startswith("text/html")

    # Should contain the JSON data
    assert "Hello from API" in page
    assert "status" in page

    # Should have JSON syntax highlighting
    assert "json-key" in page or "json-string" in page


@patch("requests.request")
def test_gateway_server_converts_json_urls_to_links(
    mock_request,
    client,
    integration_app,
):
    """Gateway should convert API URLs in JSON to clickable gateway links."""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = (
        b'{"user_url": "https://api.example.com/users/1", "repos_url": "/repos/test"}'
    )
    mock_response.text = (
        '{"user_url": "https://api.example.com/users/1", "repos_url": "/repos/test"}'
    )
    mock_response.json.return_value = {
        "user_url": "https://api.example.com/users/1",
        "repos_url": "/repos/test",
    }
    mock_request.return_value = mock_response

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    response = client.get(
        "/gateway?target_server=https://api.example.com", follow_redirects=True
    )
    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # Should have clickable links
    assert "<a href=" in page
    assert "json-url" in page


def test_gateway_server_handles_path_routing(
    client,
    integration_app,
):
    """Gateway should properly route paths after the mount point."""

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    # The gateway should accept paths after its mount point
    # Without mocking requests, it will fail to connect, but we can verify
    # it attempts to parse the path correctly
    response = client.get(
        "/gateway/users/123?target_server=https://api.example.com",
        follow_redirects=True,
    )

    # Even if the request fails, the gateway should have attempted to process it
    # (not return a 404 or routing error)
    assert response.status_code in [
        200,
        500,
    ]  # Either success or connection error, not 404


def test_gateway_server_includes_api_key_requirement_badges(
    client,
    integration_app,
):
    """Examples page should indicate which APIs require authentication."""

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # Should have auth requirement indicators
    assert "API Key Required" in page or "auth-required" in page
    assert "No Auth" in page or "no-auth" in page


def test_gateway_server_displays_instructions(
    client,
    integration_app,
):
    """Gateway examples page should include usage instructions."""

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    gateway_definition = gateway_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="gateway",
            definition=gateway_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # Should include parameter documentation
    assert "target_server" in page
    assert "request_transform" in page
    assert "response_transform" in page
    assert "How it Works" in page or "Parameters" in page
