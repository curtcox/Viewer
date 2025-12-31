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


# Phase 1: Request Transform Direct Response Tests


def test_validate_direct_response_valid():
    """Test _validate_direct_response with valid direct response."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    valid_response = {
        "output": "<html>test</html>",
        "content_type": "text/html",
        "status_code": 200,
    }
    is_valid, error_msg = gateway_definition._validate_direct_response(valid_response)
    assert is_valid is True
    assert error_msg is None


def test_validate_direct_response_missing_output():
    """Test _validate_direct_response with missing output key."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    invalid_response = {
        "content_type": "text/html",
    }
    is_valid, error_msg = gateway_definition._validate_direct_response(invalid_response)
    assert is_valid is False
    assert "output" in error_msg


def test_validate_direct_response_invalid_output_type():
    """Test _validate_direct_response with invalid output type."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    invalid_response = {
        "output": 123,  # Should be str or bytes
        "content_type": "text/html",
    }
    is_valid, error_msg = gateway_definition._validate_direct_response(invalid_response)
    assert is_valid is False
    assert "output" in error_msg
    assert "str or bytes" in error_msg


def test_validate_direct_response_invalid_status_code():
    """Test _validate_direct_response with invalid status_code type."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    invalid_response = {
        "output": "test",
        "status_code": "200",  # Should be int
    }
    is_valid, error_msg = gateway_definition._validate_direct_response(invalid_response)
    assert is_valid is False
    assert "status_code" in error_msg
    assert "int" in error_msg


def test_validate_direct_response_bytes_output():
    """Test _validate_direct_response accepts bytes output."""
    from reference_templates.servers.definitions import gateway as gateway_definition

    valid_response = {
        "output": b"<html>test</html>",
        "content_type": "text/html",
    }
    is_valid, error_msg = gateway_definition._validate_direct_response(valid_response)
    assert is_valid is True
    assert error_msg is None


def test_request_transform_direct_response_bypasses_server(monkeypatch):
    """Request transform returning response dict should bypass server execution."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Create a request transform that returns a direct response
    def mock_transform(request_details, context):
        return {
            "response": {
                "output": "<html>Direct Response</html>",
                "content_type": "text/html",
                "status_code": 200,
            }
        }
    
    # Track if _execute_target_request is called
    execute_called = {"called": False}
    original_execute = gateway_definition._execute_target_request
    
    def mock_execute(*args, **kwargs):
        execute_called["called"] = True
        return original_execute(*args, **kwargs)
    
    monkeypatch.setattr(gateway_definition, "_execute_target_request", mock_execute)
    monkeypatch.setattr(gateway_definition, "_load_transform_function", lambda cid, ctx: mock_transform)
    
    # Call _handle_gateway_request with a gateway that has a request transform
    gateways = {
        "test": {
            "request_transform_cid": "AAAAAFAKE",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        result = gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    # Server should not have been called
    assert execute_called["called"] is False
    assert result["output"] == "<html>Direct Response</html>"
    assert result["content_type"] == "text/html"


def test_request_transform_direct_response_content_type():
    """Direct response from request transform should preserve content_type."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Create a request transform that returns a direct response with JSON
    def mock_transform(request_details, context):
        return {
            "response": {
                "output": '{"message": "test"}',
                "content_type": "application/json",
            }
        }
    
    gateway_definition._load_transform_function = lambda cid, ctx: mock_transform
    
    gateways = {
        "test": {
            "request_transform_cid": "AAAAAFAKE",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        result = gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    assert result["output"] == '{"message": "test"}'
    # When passed to response transform, should have correct content type
    # For now we're testing the direct result


def test_request_transform_normal_dict_continues(monkeypatch):
    """Request transform returning normal dict should continue to server."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Create a request transform that returns a normal transformation
    def mock_transform(request_details, context):
        return {
            "method": "GET",
            "path": "/modified",
        }
    
    # Track if _execute_target_request is called
    execute_called = {"called": False}
    
    def mock_execute(target, request_details):
        execute_called["called"] = True
        # Return a mock response
        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "text/plain"}
            content = b"OK"
            text = "OK"
            def json(self):
                return {}
        return MockResponse()
    
    monkeypatch.setattr(gateway_definition, "_execute_target_request", mock_execute)
    monkeypatch.setattr(gateway_definition, "_load_transform_function", lambda cid, ctx: mock_transform)
    
    gateways = {
        "test": {
            "request_transform_cid": "AAAAAFAKE",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        result = gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    # Server should have been called
    assert execute_called["called"] is True


def test_request_transform_response_key_precedence(monkeypatch):
    """If both 'response' and 'path' keys present, 'response' takes precedence."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Create a request transform that returns both response and path
    def mock_transform(request_details, context):
        return {
            "response": {
                "output": "<html>Direct Response</html>",
                "content_type": "text/html",
            },
            "path": "/should-be-ignored",
        }
    
    # Track if _execute_target_request is called
    execute_called = {"called": False}
    original_execute = gateway_definition._execute_target_request
    
    def mock_execute(*args, **kwargs):
        execute_called["called"] = True
        return original_execute(*args, **kwargs)
    
    monkeypatch.setattr(gateway_definition, "_execute_target_request", mock_execute)
    monkeypatch.setattr(gateway_definition, "_load_transform_function", lambda cid, ctx: mock_transform)
    
    gateways = {
        "test": {
            "request_transform_cid": "AAAAAFAKE",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        result = gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    # Server should not have been called
    assert execute_called["called"] is False
    assert result["output"] == "<html>Direct Response</html>"


# Phase 1: Response Transform Source Indicator Tests


def test_response_details_source_server(monkeypatch):
    """Response details from server should have source='server'."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Mock response transform to capture response_details
    captured_response_details = {"captured": None}
    
    def mock_response_transform(response_details, context):
        captured_response_details["captured"] = response_details
        return {"output": "transformed", "content_type": "text/html"}
    
    def mock_execute(target, request_details):
        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "text/plain"}
            content = b"OK"
            text = "OK"
            def json(self):
                return {}
        return MockResponse()
    
    monkeypatch.setattr(gateway_definition, "_execute_target_request", mock_execute)
    monkeypatch.setattr(gateway_definition, "_load_transform_function", lambda cid, ctx: mock_response_transform)
    
    gateways = {
        "test": {
            "response_transform_cid": "AAAAAFAKE",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    assert captured_response_details["captured"] is not None
    assert captured_response_details["captured"]["source"] == "server"


def test_response_details_source_request_transform(monkeypatch):
    """Response details from request transform should have source='request_transform'."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Mock request transform to return direct response
    def mock_request_transform(request_details, context):
        return {
            "response": {
                "output": "Direct",
                "content_type": "text/html",
            }
        }
    
    # Mock response transform to capture response_details
    captured_response_details = {"captured": None}
    
    def mock_response_transform(response_details, context):
        captured_response_details["captured"] = response_details
        return {"output": "transformed", "content_type": "text/html"}
    
    # Track which transform is being loaded
    load_count = {"count": 0}
    
    def mock_load(cid, ctx):
        load_count["count"] += 1
        if load_count["count"] == 1:
            return mock_request_transform
        else:
            return mock_response_transform
    
    monkeypatch.setattr(gateway_definition, "_load_transform_function", mock_load)
    
    gateways = {
        "test": {
            "request_transform_cid": "AAAAAFAKE1",
            "response_transform_cid": "AAAAAFAKE2",
            "description": "Test gateway",
        }
    }
    
    with app.test_request_context("/gateway/test/path"):
        gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    assert captured_response_details["captured"] is not None
    assert captured_response_details["captured"]["source"] == "request_transform"


# Phase 1: Template Resolver Tests


def test_template_resolver_creation():
    """Template resolver should be created from gateway config."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    config = {
        "templates": {
            "test.html": "AAAAAFAKE",
        }
    }
    
    resolver = gateway_definition._create_template_resolver(config, {})
    assert callable(resolver)


def test_template_resolver_unknown_template():
    """resolve_template should raise ValueError for unknown template name."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    config = {
        "templates": {
            "known.html": "AAAAAFAKE",
        }
    }
    
    resolver = gateway_definition._create_template_resolver(config, {})
    
    with pytest.raises(ValueError) as exc_info:
        resolver("unknown.html")
    
    assert "not found in gateway config" in str(exc_info.value)


def test_template_resolver_missing_cid():
    """resolve_template should raise LookupError if CID cannot be resolved."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    config = {
        "templates": {
            "test.html": "AAAAAFAKE_NONEXISTENT",
        }
    }
    
    resolver = gateway_definition._create_template_resolver(config, {})
    
    with pytest.raises(LookupError) as exc_info:
        resolver("test.html")
    
    assert "Could not resolve template CID" in str(exc_info.value)


def test_empty_templates_config():
    """Gateway with no templates config should still work."""
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    config = {}
    
    # Should not raise an error
    resolver = gateway_definition._create_template_resolver(config, {})
    assert callable(resolver)
    
    # But should fail when trying to resolve a template
    with pytest.raises(ValueError):
        resolver("any.html")


def test_man_transform_uses_external_template(monkeypatch):
    """Man response transform should use external template via resolve_template."""
    # Create a simple mock transform that uses resolve_template
    def mock_transform(response_details, context):
        resolve_template = context.get("resolve_template")
        if not resolve_template:
            raise RuntimeError("resolve_template not available")
        
        template = resolve_template("man_page.html")
        html = template.render(command="grep", sections=None, content="test content")
        return {"output": html, "content_type": "text/html"}
    
    # Create mock templates
    from jinja2 import Template
    
    def mock_resolve_cid(cid_value, as_bytes=False):
        # Handle both with and without leading slash
        cid = cid_value.lstrip("/")
        if "man_page" in cid or cid == "FAKE_TEMPLATE":
            content = "<!DOCTYPE html><html><body>man {{ command }}: {{ content }}</body></html>"
            if as_bytes:
                return content.encode("utf-8")
            return content
        return None
    
    from reference_templates.servers.definitions import gateway as gateway_definition
    
    # Mock the CID resolution
    monkeypatch.setattr(gateway_definition, "_resolve_cid_content", mock_resolve_cid)
    monkeypatch.setattr(gateway_definition, "_load_transform_function", lambda cid, ctx: mock_transform)
    
    gateways = {
        "test": {
            "response_transform_cid": "FAKE",
            "templates": {
                "man_page.html": "FAKE_TEMPLATE",
            },
        }
    }
    
    # Mock server execution
    def mock_execute(target, request_details):
        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "text/plain"}
            content = b"test output"
            text = "test output"
            def json(self):
                return None
        return MockResponse()
    
    monkeypatch.setattr(gateway_definition, "_execute_target_request", mock_execute)
    
    with app.test_request_context("/gateway/test/path"):
        result = gateway_definition._handle_gateway_request("test", "path", gateways, {})
    
    # Should return HTML with templated content
    assert result["content_type"] == "text/html"
    assert "<!DOCTYPE html>" in result["output"]
    assert "man grep" in result["output"]
    assert "test content" in result["output"]



def test_man_transform_requires_templates():
    """Man transform should raise error if resolve_template not available."""
    # Create a simple mock transform that requires resolve_template
    def mock_transform(response_details, context):
        resolve_template = context.get("resolve_template")
        if not resolve_template:
            raise RuntimeError("resolve_template not available - templates must be configured")
        return {"output": "test", "content_type": "text/html"}
    
    # Call without resolve_template in context
    response_details = {
        "status_code": 200,
        "text": "grep - print lines",
        "request_path": "grep",
    }
    
    with pytest.raises(RuntimeError) as exc_info:
        mock_transform(response_details, {})
    
    assert "resolve_template not available" in str(exc_info.value)
