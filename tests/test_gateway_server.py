"""Tests for gateway server functionality."""
# pylint: disable=no-name-in-module

from unittest.mock import Mock, patch

import pytest

import server_execution
from app import app


@pytest.fixture(autouse=True)
def patch_execution_environment(monkeypatch):
    """Patch the execution environment for gateway tests."""
    from server_execution import code_execution

    monkeypatch.setattr(
        code_execution,
        "_load_user_context",
        lambda: {"variables": {}, "secrets": {}, "servers": {}},
    )

    def fake_success(output, content_type, server_name, *, external_calls=None):
        return {
            "output": output,
            "content_type": content_type,
            "server_name": server_name,
        }

    monkeypatch.setattr(code_execution, "_handle_successful_execution", fake_success)


def test_gateway_server_template_exists():
    """Verify that the gateway server template is registered."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_templates = [t for t in templates if t.get("id") == "gateway"]

    assert gateway_templates, "Gateway template should be registered"
    assert gateway_templates[0]["name"] == "Gateway Server"
    assert "definition" in gateway_templates[0]


def test_gateway_shows_examples_page_without_target_server():
    """When no target_server is provided, gateway should show examples page."""
    # Load the actual gateway definition
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway"):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    assert result["content_type"] == "text/html"
    assert "Gateway Server" in result["output"]
    assert "API Examples" in result["output"]
    assert "GitHub API" in result["output"]
    assert "OpenAI API" in result["output"]


def test_gateway_includes_all_required_api_examples():
    """Gateway examples page should include all required API providers."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway"):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    output = result["output"]
    required_apis = [
        "GitHub API",
        "OpenAI API",
        "Anthropic API",
        "Google",
        "OpenRouter",
        "Eleven Labs",
        "Vercel",
    ]

    for api in required_apis:
        assert api in output, f"{api} should be in examples page"


@patch("requests.request")
def test_gateway_proxies_request_to_target_server(mock_request):
    """Gateway should proxy requests to the target server."""
    # Mock the response from the target server
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b'{"message": "Hello from API"}'
    mock_response.text = '{"message": "Hello from API"}'
    mock_response.json.return_value = {"message": "Hello from API"}
    mock_request.return_value = mock_response

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context(
        "/gateway/test?target_server=https://api.example.com"
    ):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    assert result["content_type"] == "text/html"
    assert "Hello from API" in result["output"]


@patch("requests.request")
def test_gateway_converts_json_to_html(mock_request):
    """Gateway should convert JSON responses to formatted HTML."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b'{"key": "value", "number": 42}'
    mock_response.text = '{"key": "value", "number": 42}'
    mock_response.json.return_value = {"key": "value", "number": 42}
    mock_request.return_value = mock_response

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context(
        "/gateway/endpoint?target_server=https://api.example.com"
    ):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    assert result["content_type"] == "text/html"
    assert "json-key" in result["output"]  # CSS class for JSON keys
    assert "json-string" in result["output"]  # CSS class for JSON strings
    assert "json-number" in result["output"]  # CSS class for JSON numbers


@patch("requests.request")
def test_gateway_creates_links_for_api_urls(mock_request):
    """Gateway should convert API URLs in JSON responses to clickable links."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b'{"url": "https://api.example.com/users/1"}'
    mock_response.text = '{"url": "https://api.example.com/users/1"}'
    mock_response.json.return_value = {"url": "https://api.example.com/users/1"}
    mock_request.return_value = mock_response

    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context(
        "/gateway?target_server=https://api.example.com"
    ):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    assert result["content_type"] == "text/html"
    # The URL should be converted to a clickable link
    assert "<a href=" in result["output"]
    assert "json-url" in result["output"]


def test_gateway_uses_path_after_mount_point():
    """Gateway should use the path after /gateway as the target path."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    
    # Verify the definition contains path handling logic
    definition = gateway_template["definition"]
    assert "request_path" in definition
    assert "path_parts" in definition


def test_gateway_handles_missing_target_server_gracefully():
    """Gateway should gracefully handle missing target_server parameter."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway"):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    # Should show examples page, not error
    assert result["content_type"] == "text/html"
    assert "Gateway Server" in result["output"]
    assert "API Examples" in result["output"]


def test_gateway_definition_includes_transform_parameters():
    """Gateway definition should support request_transform and response_transform."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    # Check that the definition mentions both transform parameters
    assert "request_transform" in definition
    assert "response_transform" in definition
    assert "_apply_transform" in definition


def test_gateway_examples_page_includes_instructions():
    """Examples page should include instructions on how to use the gateway."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway"):
        result = server_execution.execute_server_code_from_definition(definition, "gateway")

    output = result["output"]
    assert "How it Works" in output
    assert "Parameters" in output
    assert "target_server" in output
    assert "request_transform" in output
    assert "response_transform" in output


def test_gateway_template_has_correct_metadata():
    """Gateway template should have proper id, name, and description."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_templates = [t for t in templates if t.get("id") == "gateway"]

    assert len(gateway_templates) == 1
    gateway = gateway_templates[0]

    assert gateway["id"] == "gateway"
    assert gateway["name"] == "Gateway Server"
    assert "proxy" in gateway["description"].lower()
    assert "REST API" in gateway["description"]
