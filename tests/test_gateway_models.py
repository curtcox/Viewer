"""Tests for gateway.models module."""

import pytest
from gateway_lib.models import (
    GatewayConfig,
    RequestDetails,
    ResponseDetails,
    TransformResult,
    Target,
    DirectResponse,
)


class TestGatewayConfig:
    """Tests for GatewayConfig dataclass."""
    
    def test_create_minimal_config(self):
        """Test creating gateway config with only required fields."""
        config = GatewayConfig(name="test")
        assert config.name == "test"
        assert config.request_transform_cid is None
        assert config.response_transform_cid is None
        assert config.templates == {}
        assert config.target_url is None
        assert config.custom_error_template_cid is None
    
    def test_create_full_config(self):
        """Test creating gateway config with all fields."""
        config = GatewayConfig(
            name="test",
            request_transform_cid="/CID1",
            response_transform_cid="/CID2",
            templates={"template.html": "/CID3"},
            target_url="/test/target",
            custom_error_template_cid="/CID4",
        )
        assert config.name == "test"
        assert config.request_transform_cid == "/CID1"
        assert config.response_transform_cid == "/CID2"
        assert config.templates == {"template.html": "/CID3"}
        assert config.target_url == "/test/target"
        assert config.custom_error_template_cid == "/CID4"


class TestRequestDetails:
    """Tests for RequestDetails dataclass."""
    
    def test_create_minimal_request(self):
        """Test creating request details with only path."""
        req = RequestDetails(path="/test")
        assert req.path == "/test"
        assert req.method == "GET"
        assert req.query_string == ""
        assert req.headers == {}
        assert req.json is None
        assert req.data is None
        assert req.url is None
    
    def test_create_full_request(self):
        """Test creating request details with all fields."""
        req = RequestDetails(
            path="/test",
            method="POST",
            query_string="key=value",
            headers={"Content-Type": "application/json"},
            json={"data": "value"},
            data='{"data": "value"}',
            url="http://localhost/test",
        )
        assert req.path == "/test"
        assert req.method == "POST"
        assert req.query_string == "key=value"
        assert req.headers == {"Content-Type": "application/json"}
        assert req.json == {"data": "value"}
        assert req.data == '{"data": "value"}'
        assert req.url == "http://localhost/test"
    
    def test_from_params(self):
        """Test building RequestDetails from parameters."""
        req = RequestDetails.from_params(
            path="/test",
            method="POST",
            headers={"X-Custom": "value"}
        )
        assert req.path == "/test"
        assert req.method == "POST"
        assert req.headers == {"X-Custom": "value"}


class TestResponseDetails:
    """Tests for ResponseDetails dataclass."""
    
    def test_create_response(self):
        """Test creating response details."""
        resp = ResponseDetails(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"<html></html>",
            text="<html></html>",
        )
        assert resp.status_code == 200
        assert resp.headers == {"Content-Type": "text/html"}
        assert resp.content == b"<html></html>"
        assert resp.text == "<html></html>"
        assert resp.json is None
        assert resp.request_path == ""
        assert resp.source == "server"
        assert resp.is_direct_response is False
    
    def test_response_with_json(self):
        """Test response with JSON data."""
        resp = ResponseDetails(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"key": "value"}',
            text='{"key": "value"}',
            json={"key": "value"},
        )
        assert resp.json == {"key": "value"}
    
    def test_direct_response_flag(self):
        """Test direct response flag."""
        resp = ResponseDetails(
            status_code=200,
            headers={},
            content=b"",
            text="",
            is_direct_response=True,
            source="request_transform",
        )
        assert resp.is_direct_response is True
        assert resp.source == "request_transform"


class TestTransformResult:
    """Tests for TransformResult dataclass."""
    
    def test_create_transform_result(self):
        """Test creating transform result."""
        result = TransformResult(output="Hello")
        assert result.output == "Hello"
        assert result.content_type == "text/plain"
        assert result.status_code == 200
        assert result.headers is None
    
    def test_transform_result_with_bytes(self):
        """Test transform result with bytes output."""
        result = TransformResult(
            output=b"binary data",
            content_type="application/octet-stream",
        )
        assert result.output == b"binary data"
        assert result.content_type == "application/octet-stream"
    
    def test_transform_result_with_headers(self):
        """Test transform result with custom headers."""
        result = TransformResult(
            output="<html></html>",
            content_type="text/html",
            status_code=201,
            headers={"X-Custom": "value"},
        )
        assert result.status_code == 201
        assert result.headers == {"X-Custom": "value"}


class TestTarget:
    """Tests for Target dataclass."""
    
    def test_create_internal_target(self):
        """Test creating internal target."""
        target = Target(mode="internal", url="/test")
        assert target.mode == "internal"
        assert target.url == "/test"
    
    def test_validate_internal_target(self):
        """Test validating internal target."""
        target = Target(mode="internal", url="/test")
        target.validate()  # Should not raise
    
    def test_validate_rejects_external_mode(self):
        """Test validation rejects external mode."""
        target = Target(mode="external", url="http://example.com")
        with pytest.raises(ValueError, match="Unsupported target mode"):
            target.validate()
    
    def test_validate_rejects_external_url(self):
        """Test validation rejects external URL."""
        target = Target(mode="internal", url="http://example.com")
        with pytest.raises(ValueError, match="must be an internal path"):
            target.validate()


class TestDirectResponse:
    """Tests for DirectResponse dataclass."""
    
    def test_create_direct_response(self):
        """Test creating direct response."""
        resp = DirectResponse(output="<html></html>")
        assert resp.output == "<html></html>"
        assert resp.content_type == "text/html"
        assert resp.status_code == 200
        assert resp.headers is None
    
    def test_direct_response_with_custom_fields(self):
        """Test direct response with custom fields."""
        resp = DirectResponse(
            output=b"binary",
            content_type="application/octet-stream",
            status_code=201,
            headers={"X-Custom": "value"},
        )
        assert resp.output == b"binary"
        assert resp.content_type == "application/octet-stream"
        assert resp.status_code == 201
        assert resp.headers == {"X-Custom": "value"}
