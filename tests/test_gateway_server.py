"""Tests for gateway server functionality."""
# pylint: disable=no-name-in-module

import gzip
from unittest.mock import Mock, patch

import pytest

import server_execution
from app import app


@pytest.fixture(autouse=True)
def patch_execution_environment(monkeypatch):
    """Patch the execution environment for gateway tests."""
    from server_execution import code_execution

    # Provide a mock context with gateways variable
    import json

    gateways_config = {
        "jsonplaceholder": {
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": "",
            "response_transform_cid": "",
        },
    }

    monkeypatch.setattr(
        code_execution,
        "_load_user_context",
        lambda: {
            "variables": {"gateways": json.dumps(gateways_config)},
            "secrets": {},
            "servers": {},
        },
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


def test_gateway_shows_instruction_page_with_gateways():
    """Gateway should show instruction page with configured gateways."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway"):
        result = server_execution.execute_server_code_from_definition(
            definition, "gateway"
        )

    assert result["content_type"] == "text/html"
    assert "Gateway Server" in result["output"]


def test_gateway_template_has_correct_metadata():
    """Gateway template should have proper id, name, and description."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_templates = [t for t in templates if t.get("id") == "gateway"]

    assert len(gateway_templates) == 1
    gateway = gateway_templates[0]

    assert gateway["id"] == "gateway"
    assert gateway["name"] == "Gateway Server"
    assert "proxy" in gateway["description"].lower() or "api" in gateway["description"].lower()


def test_gateway_handles_missing_gateway_gracefully():
    """Gateway should handle requests to non-existent gateways gracefully."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway/nonexistent-api/test"):
        result = server_execution.execute_server_code_from_definition(
            definition, "gateway"
        )

    assert result["content_type"] == "text/html"
    # Should show error about gateway not found
    assert "Not Found" in result["output"] or "not configured" in result["output"].lower()
    assert "Defined gateways" in result["output"]
    assert "jsonplaceholder" in result["output"]


def test_gateway_internal_redirect_resolution_preserves_bytes():
    """Gateway should resolve internal redirects to CID content without corrupting raw bytes."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    raw_json = b"{\"ok\": true}"

    class _FakeResponse:
        status_code = 302
        headers = {"Location": "/AAAAATEST.json"}
        content = b""
        text = ""

    with patch.object(gateway_definition, "_resolve_cid_content", return_value=raw_json) as mock_resolve:
        resolved = gateway_definition._follow_internal_redirects(_FakeResponse())

    mock_resolve.assert_called_once_with("AAAAATEST", as_bytes=True)
    assert getattr(resolved, "status_code", None) == 200
    assert resolved.content == raw_json
    assert resolved.headers.get("Content-Type") == "application/json"


@patch("requests.request")
def test_internal_jsonplaceholder_forces_identity_encoding(mock_request):
    """Internal jsonplaceholder server should force identity encoding to avoid compressed bytes."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b"{}"
    mock_request.return_value = mock_response

    from reference_templates.servers.definitions import jsonplaceholder as jsonplaceholder_definition

    class _FakeReq:
        path = "/jsonplaceholder/posts/1"
        query_string = b""
        method = "GET"
        headers = {"Accept-Encoding": "br"}

        def get_data(self, cache=False):  # pylint: disable=unused-argument
            return None

    jsonplaceholder_definition._proxy_request(_FakeReq())

    assert mock_request.call_count == 1
    _, kwargs = mock_request.call_args
    lowered = {k.lower(): v for k, v in (kwargs.get("headers") or {}).items()}
    assert lowered.get("accept-encoding") == "identity"


@patch("requests.request")
def test_internal_jsonplaceholder_decompresses_gzip(mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
    }
    payload = b"{\"ok\": true}"
    mock_response.content = gzip.compress(payload)
    mock_request.return_value = mock_response

    from reference_templates.servers.definitions import jsonplaceholder as jsonplaceholder_definition

    class _FakeReq:
        path = "/jsonplaceholder/posts/1"
        query_string = b""
        method = "GET"
        headers = {}

        def get_data(self, cache=False):  # pylint: disable=unused-argument
            return None

    result = jsonplaceholder_definition._proxy_request(_FakeReq())

    assert result["content_type"] == "application/json"
    assert result["output"] == payload


def test_gateway_request_route_accessible():
    """Gateway /request route should be accessible."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway/request"):
        result = server_execution.execute_server_code_from_definition(
            definition, "gateway"
        )

    assert result["content_type"] == "text/html"
    # Should render request form
    assert "Request" in result["output"]


def test_gateway_response_route_accessible():
    """Gateway /response route should be accessible."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway/response"):
        result = server_execution.execute_server_code_from_definition(
            definition, "gateway"
        )

    assert result["content_type"] == "text/html"
    # Should render response form
    assert "Response" in result["output"]


@patch("requests.request")
def test_gateway_man_executes_internally_without_http(mock_request):
    """Gateway should execute internal targets (like man) without HTTP requests."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    gateway_template = next(t for t in templates if t.get("id") == "gateway")
    definition = gateway_template["definition"]

    with app.test_request_context("/gateway/man/grep"):
        result = server_execution.execute_server_code_from_definition(
            definition, "gateway"
        )

    mock_request.assert_not_called()
    assert result["content_type"] == "text/html"
    assert "Failed to connect" not in result["output"]
    assert "<html" in result["output"].lower()
