"""Integration tests for gateway server functionality."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from database import db
from models import Server, Variable

pytestmark = pytest.mark.integration


@pytest.fixture
def gateway_server(integration_app):
    """Create the gateway server."""
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

    return gateway_definition


@pytest.fixture
def gateways_variable(integration_app):
    """Create the gateways variable with test configuration."""
    import json

    gateways_config = {
        "jsonplaceholder": {
            "target_url": "https://jsonplaceholder.typicode.com",
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": "",
            "response_transform_cid": "",
        },
        "test-api": {
            "target_url": "https://api.example.com",
            "description": "Test API for unit testing",
            "request_transform_cid": "",
            "response_transform_cid": "",
        },
    }

    with integration_app.app_context():
        variable = Variable(
            name="gateways",
            definition=json.dumps(gateways_config),
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()

    return gateways_config


def _create_transform_cid(integration_app, source: str) -> str:
    from cid_utils import generate_cid
    from db_access import create_cid_record

    cid_value = generate_cid(source.encode("utf-8"))
    with integration_app.app_context():
        create_cid_record(cid_value, source.encode("utf-8"))
    return cid_value


@pytest.fixture
def gateways_variable_with_transforms(integration_app):
    """Create a gateways variable that points at CID-stored transforms."""
    import json

    request_transform_source = """
def transform_request(request_details: dict, context: dict) -> dict:
    return {"method": "GET", "headers": {"Accept": "text/plain"}}
""".lstrip()

    response_transform_source = """
def transform_response(response_details: dict, context: dict) -> dict:
    return {"output": "<html><body>ok</body></html>", "content_type": "text/html"}
""".lstrip()

    request_cid = _create_transform_cid(integration_app, request_transform_source)
    response_cid = _create_transform_cid(integration_app, response_transform_source)

    gateways_config = {
        "jsonplaceholder": {
            "target_url": "https://jsonplaceholder.typicode.com",
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": request_cid,
            "response_transform_cid": response_cid,
        },
    }

    with integration_app.app_context():
        variable = Variable(
            name="gateways",
            definition=json.dumps(gateways_config),
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()

    return gateways_config


def test_gateway_shows_instruction_page(
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway server should show instruction page with configured gateways."""
    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Gateway Server" in page
    assert "jsonplaceholder" in page
    assert "test-api" in page


def test_gateway_shows_instruction_page_without_gateways_variable(
    client,
    integration_app,
    gateway_server,
):
    """Gateway should gracefully handle missing gateways variable."""
    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Gateway Server" in page
    # Should show empty state or instructions
    assert "No gateways configured" in page or "Gateway Server" in page


def test_gateway_request_form_accessible(
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway request form should be accessible."""
    response = client.get("/gateway/request", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Request" in page


def test_gateway_response_form_accessible(
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway response form should be accessible."""
    response = client.get("/gateway/response", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Response" in page


def test_gateway_meta_page_shows_config(
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway meta page should show gateway configuration."""
    response = client.get("/gateway/meta/jsonplaceholder", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "jsonplaceholder" in page
    assert "jsonplaceholder.typicode.com" in page


def test_gateway_meta_page_finds_transform_cids(
    client,
    integration_app,
    gateway_server,
    gateways_variable_with_transforms,
):
    """Gateway meta page should validate transforms stored as DB CIDs even without a leading slash."""
    response = client.get("/gateway/meta/jsonplaceholder", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Request Transform" in page
    assert "Response Transform" in page
    assert "Valid" in page


@patch("requests.request")
def test_gateway_meta_page_includes_downstream_probe(
    mock_request,
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway meta page should include target resolution and a downstream probe preview."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.content = b"ok"
    mock_response.text = "ok"
    mock_request.return_value = mock_response

    response = client.get("/gateway/meta/jsonplaceholder", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Target Resolution" in page
    assert "Downstream Probe" in page


@patch("requests.request")
def test_gateway_returns_error_when_response_transform_missing(
    mock_request,
    client,
    integration_app,
    gateway_server,
):
    """Gateway should return an error page when a configured response transform cannot be loaded."""
    import json

    gateways_config = {
        "jsonplaceholder": {
            "target_url": "https://jsonplaceholder.typicode.com",
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": "",
            "response_transform_cid": "AAAAA_DOES_NOT_EXIST",
        },
    }

    with integration_app.app_context():
        variable = Variable(
            name="gateways",
            definition=json.dumps(gateways_config),
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.content = b"RAW"
    mock_response.text = "RAW"
    mock_request.return_value = mock_response

    response = client.get("/gateway/jsonplaceholder/posts/1", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Response Transform Not Found" in page


def test_gateway_meta_page_404_for_unknown_gateway(
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway meta page should show error for unknown gateway."""
    response = client.get("/gateway/meta/unknown-gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Not Found" in page or "unknown-gateway" in page


@patch("requests.request")
def test_gateway_proxies_to_target(
    mock_request,
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway should proxy requests to the target server."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.content = b'{"message": "Hello from API", "status": "ok"}'
    mock_response.text = '{"message": "Hello from API", "status": "ok"}'
    mock_response.json.return_value = {"message": "Hello from API", "status": "ok"}
    mock_request.return_value = mock_response

    response = client.get("/gateway/jsonplaceholder/posts/1", follow_redirects=True)
    assert response.status_code == 200

    # Verify the request was made to the target
    mock_request.assert_called()


@patch("requests.request")
def test_gateway_handles_request_errors(
    mock_request,
    client,
    integration_app,
    gateway_server,
    gateways_variable,
):
    """Gateway should handle target server errors gracefully."""
    mock_request.side_effect = Exception("Connection failed")

    response = client.get("/gateway/jsonplaceholder/posts/1", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show error page
    assert "Error" in page or "Failed" in page


def test_gateway_error_page_includes_diagnostics(
    client,
    integration_app,
    gateway_server,
):
    """Error page should include diagnostic information when available."""
    # Request a gateway that doesn't exist
    response = client.get("/gateway/nonexistent-gateway/test", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show gateway not found error
    assert "Not Found" in page or "not configured" in page.lower()
    assert "Defined gateways" in page
