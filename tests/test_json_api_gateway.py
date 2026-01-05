"""Tests for JSON API Gateway functionality."""
import pytest

from app import app


@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_json_api_gateway_basic_json_rendering(client):
    """Test that JSON API gateway renders JSON with syntax highlighting."""
    # This test will verify basic JSON rendering without needing a real server
    # We'll use the response transform directly
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links
    )

    # Test basic JSON formatting
    test_json = {
        "id": 1,
        "name": "Test",
        "value": 42,
        "active": True,
        "notes": None
    }

    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {"enabled": False}
    }

    result = _format_json_with_links(test_json, link_config, "", 0)

    # Verify JSON structure is preserved
    assert '"id"' in result
    assert '"name"' in result
    assert '"value"' in result
    assert '"active"' in result
    assert '"notes"' in result

    # Verify syntax highlighting classes
    assert 'json-key' in result
    assert 'json-string' in result
    assert 'json-number' in result
    assert 'json-boolean' in result
    assert 'json-null' in result


def test_json_api_gateway_id_reference_detection(client):
    """Test that ID reference detection creates proper links."""
    from reference_templates.gateways.transforms.json_api_response import (
        _detect_id_reference_link
    )

    link_config = {
        "id_reference": {
            "enabled": True,
            "patterns": {
                "userId": "/gateway/json_api/users/{id}",
                "postId": "/gateway/json_api/posts/{id}"
            }
        }
    }

    # Test userId detection
    result = _detect_id_reference_link("userId", 1, link_config, "")
    assert result == "/gateway/json_api/users/1"

    # Test postId detection
    result = _detect_id_reference_link("postId", 42, link_config, "")
    assert result == "/gateway/json_api/posts/42"

    # Test non-matching key
    result = _detect_id_reference_link("otherId", 1, link_config, "")
    assert result is None


def test_json_api_gateway_full_url_detection(client):
    """Test that full URL detection works correctly."""
    from reference_templates.gateways.transforms.json_api_response import (
        _detect_full_url_link
    )

    link_config = {
        "full_url": {
            "enabled": True,
            "base_url_strip": "https://jsonplaceholder.typicode.com",
            "gateway_prefix": "/gateway/json_api"
        }
    }

    # Test URL with base stripping
    result = _detect_full_url_link(
        "https://jsonplaceholder.typicode.com/users/1",
        link_config
    )
    assert result == "/gateway/json_api/users/1"

    # Test external URL (no stripping)
    result = _detect_full_url_link(
        "https://example.com/api/test",
        link_config
    )
    assert result == "https://example.com/api/test"

    # Test non-URL string
    result = _detect_full_url_link("not a url", link_config)
    assert result is None


def test_json_api_gateway_partial_url_detection(client):
    """Test that partial (path-only) URL detection works correctly."""
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links
    )

    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {"enabled": False},
        "partial_url": {
            "enabled": True,
            "key_patterns": ["url", "*_url", "*_path", "href"],
            "gateway_prefix": "/gateway/stripe",
        },
    }

    # Key matches pattern and value is a path => linked
    test_json = {"url": "/v1/customers"}
    result = _format_json_with_links(test_json, link_config, "", 0)
    assert "/gateway/stripe/v1/customers" in result
    assert "json-link" in result

    # Key does not match pattern => not linked
    test_json = {"not_url": "/v1/customers"}
    result = _format_json_with_links(test_json, link_config, "", 0)
    assert "/gateway/stripe/v1/customers" not in result


def test_json_api_gateway_composite_reference_detection(client):
    """Test composite reference detection (context-aware) using request_path regex."""
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links,
    )

    link_config = {
        "full_url": {"enabled": False},
        "partial_url": {"enabled": False},
        "id_reference": {"enabled": False},
        "composite_reference": {
            "enabled": True,
            "patterns": {
                "number": [
                    {
                        "context_regex": r"^/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)",
                        "url_template": "/gateway/github/repos/{owner}/{repo}/issues/{id}",
                    }
                ]
            },
        },
    }

    request_path = "/repos/octocat/Hello-World/issues"
    test_json = {"number": 123}

    result = _format_json_with_links(test_json, link_config, request_path, 0)
    assert "/gateway/github/repos/octocat/Hello-World/issues/123" in result
    assert "json-link" in result


def test_json_api_gateway_array_handling(client):
    """Test that arrays are formatted correctly."""
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links
    )

    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {"enabled": False}
    }

    # Test empty array
    result = _format_json_with_links([], link_config, "", 0)
    assert result == "[]"

    # Test array of primitives
    result = _format_json_with_links([1, 2, 3], link_config, "", 0)
    assert "json-number" in result
    assert "1" in result and "2" in result and "3" in result

    # Test array of objects
    test_array = [
        {"id": 1, "name": "First"},
        {"id": 2, "name": "Second"}
    ]
    result = _format_json_with_links(test_array, link_config, "", 0)
    assert '"id"' in result
    assert '"name"' in result


def test_json_api_gateway_nested_objects(client):
    """Test that nested objects are handled correctly."""
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links
    )

    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {"enabled": False}
    }

    test_nested = {
        "user": {
            "id": 1,
            "profile": {
                "name": "Test User",
                "age": 30
            }
        }
    }

    result = _format_json_with_links(test_nested, link_config, "", 0)
    assert '"user"' in result
    assert '"profile"' in result
    assert '"name"' in result
    assert '"age"' in result


def test_json_api_gateway_breadcrumb_generation(client):
    """Test breadcrumb navigation generation."""
    from reference_templates.gateways.transforms.json_api_response import (
        _build_breadcrumb
    )

    # Test root path
    result = _build_breadcrumb("", "json_api")
    assert "json_api" in result
    assert "/gateway/json_api" in result

    # Test nested path
    result = _build_breadcrumb("users/1/posts", "json_api")
    assert "users" in result
    assert "posts" in result
    assert "/gateway/json_api/users" in result


def test_json_api_gateway_with_id_references_in_json(client):
    """Test complete JSON formatting with ID reference links."""
    from reference_templates.gateways.transforms.json_api_response import (
        _format_json_with_links
    )

    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {
            "enabled": True,
            "patterns": {
                "userId": "/gateway/json_api/users/{id}",
                "postId": "/gateway/json_api/posts/{id}"
            }
        }
    }

    test_json = {
        "id": 1,
        "title": "Test Post",
        "userId": 5,
        "postId": 10
    }

    result = _format_json_with_links(test_json, link_config, "", 0)

    # Verify links are created
    assert "/gateway/json_api/users/5" in result
    assert "/gateway/json_api/posts/10" in result
    assert 'json-link' in result

    # Verify non-linked fields are still present
    assert '"title"' in result
    assert '"id"' in result
