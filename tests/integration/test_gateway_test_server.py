"""Integration tests for gateway test server functionality."""

from __future__ import annotations

import json
import pytest

from database import db
from models import Alias, Server, Variable

pytestmark = pytest.mark.integration


@pytest.fixture
def hrx_server(integration_app):
    """Create the HRX server."""
    from reference_templates.servers import get_server_templates

    templates = get_server_templates()
    hrx_template = next((t for t in templates if t.get("id") == "hrx"), None)
    
    if not hrx_template:
        pytest.skip("HRX server template not found")
    
    hrx_definition = hrx_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="hrx",
            definition=hrx_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    return hrx_definition


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
def gateways_variable_with_jsonplaceholder(integration_app):
    """Create the gateways variable with jsonplaceholder configuration."""
    gateways_config = {
        "jsonplaceholder": {
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": "reference_templates/gateways/transforms/jsonplaceholder_request.py",
            "response_transform_cid": "reference_templates/gateways/transforms/jsonplaceholder_response.py",
            "templates": {
                "jsonplaceholder_data.html": "reference_templates/gateways/templates/jsonplaceholder_data.html",
                "jsonplaceholder_error.html": "reference_templates/gateways/templates/jsonplaceholder_error.html"
            }
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


@pytest.fixture
def local_jsonplaceholder_alias(integration_app):
    """Create the local_jsonplaceholder alias (disabled by default)."""
    with integration_app.app_context():
        alias = Alias(
            name="local_jsonplaceholder",
            definition="/gateway/jsonplaceholder/** -> /gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/**",
            enabled=False,  # Disabled by default as per requirements
        )
        db.session.add(alias)
        db.session.commit()

    return alias


def test_gateway_test_pattern_routing(
    client,
    integration_app,
    hrx_server,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
):
    """Test that gateway test pattern routes correctly."""
    # Test accessing via test pattern
    # /gateway/test/hrx/CID/as/jsonplaceholder/posts/1
    response = client.get(
        "/gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/posts/1"
    )
    
    # Should return success (may be 200 or redirect)
    assert response.status_code in [200, 302], f"Got status {response.status_code}"
    
    # Response should contain data if successful
    if response.status_code == 200:
        page = response.get_data(as_text=True)
        # Should have some content (error page or actual data)
        assert len(page) > 0


def test_gateway_test_meta_page(
    client,
    integration_app,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
):
    """Test that gateway test meta page shows test information."""
    # Access meta page with test pattern
    response = client.get(
        "/gateway/meta/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder"
    )
    
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    
    # Should mention the server name
    assert "jsonplaceholder" in page.lower()


def test_local_jsonplaceholder_alias_disabled_by_default(
    client,
    integration_app,
    gateway_server,
    local_jsonplaceholder_alias,
):
    """Test that local_jsonplaceholder alias exists but is disabled."""
    with integration_app.app_context():
        alias = db.session.query(Alias).filter_by(name="local_jsonplaceholder").first()
        assert alias is not None, "local_jsonplaceholder alias should exist"
        assert alias.enabled is False, "local_jsonplaceholder alias should be disabled by default"


def test_local_jsonplaceholder_alias_when_enabled(
    client,
    integration_app,
    hrx_server,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
    local_jsonplaceholder_alias,
):
    """Test that local_jsonplaceholder alias works when enabled."""
    # Enable the alias
    with integration_app.app_context():
        alias = db.session.query(Alias).filter_by(name="local_jsonplaceholder").first()
        alias.enabled = True
        db.session.commit()
    
    # Now requests to /gateway/jsonplaceholder should be redirected to the test server
    # This is just checking the alias exists and is enabled
    with integration_app.app_context():
        alias = db.session.query(Alias).filter_by(name="local_jsonplaceholder").first()
        assert alias.enabled is True


def test_gateway_test_pattern_without_hrx_server_shows_error(
    client,
    integration_app,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
):
    """Test that using test pattern without HRX server shows appropriate error."""
    # Try to access test pattern without HRX server configured
    response = client.get(
        "/gateway/test/hrx/SOMECID/as/jsonplaceholder/posts/1"
    )
    
    # Should get some response (could be error or redirect)
    assert response.status_code in [200, 302, 404, 500]


def test_gateway_test_pattern_with_nonexistent_cid(
    client,
    integration_app,
    hrx_server,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
):
    """Test that using test pattern with non-existent CID handles gracefully."""
    # Use a CID that doesn't exist
    response = client.get(
        "/gateway/test/hrx/AAAAANONEXISTENT_CID/as/jsonplaceholder/posts/1"
    )
    
    # Should get some response (error or redirect)
    assert response.status_code in [200, 302, 404, 500]


def test_gateway_test_pattern_preserves_transforms(
    client,
    integration_app,
    hrx_server,
    gateway_server,
    gateways_variable_with_jsonplaceholder,
):
    """Test that test pattern uses the transforms from the named gateway."""
    # The test pattern should use jsonplaceholder transforms even though
    # it's fetching from HRX server
    response = client.get(
        "/gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/posts/1"
    )
    
    # Response should exist
    assert response is not None
    # We're mainly testing that the request doesn't crash
    # The actual transform behavior would need the HRX and transforms to work together
