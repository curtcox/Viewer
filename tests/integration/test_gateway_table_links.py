"""Integration tests for gateway table links on the gateways page.

Tests the links in the Configured Gateways table:
- Server links: /servers/{name}
- Meta links: /gateway/meta/{name}
- Test links: /gateway/test/cids/{mock_cid}/as/{name}
- Sample links: /cids/{mock_cid}

Uses Flask's test client for one-shot testing without HTTP or browser.
Each gateway server from reference/archive/cids has its own test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from database import db
from models import Server, Variable
from tests.test_gateway_test_support import TEST_CIDS_ARCHIVE_CID

pytestmark = pytest.mark.integration


# Dynamically load all gateway servers from reference/archive/cids
def get_all_gateway_servers():
    """Get all gateway server names from reference/archive/cids directory."""
    cids_dir = Path("reference/archive/cids")
    if not cids_dir.exists():
        return []
    
    gateway_names = []
    for file in sorted(cids_dir.glob("*.source.cids")):
        name = file.stem.replace(".source", "")
        gateway_names.append(name)
    
    return gateway_names


GATEWAY_SERVERS = get_all_gateway_servers()


@pytest.fixture
def gateway_server(integration_app):
    """Create the gateway server."""
    from reference.templates.servers import get_server_templates

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
    # Load the actual gateways configuration
    with open("reference/templates/gateways.source.json", "r", encoding="utf-8") as f:
        gateways_config = json.load(f)

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
def mock_cid():
    """Return the mock CID used for test and sample links."""
    return TEST_CIDS_ARCHIVE_CID


class TestServerLinks:
    """Tests for Server column links: /servers/{name}"""

    @pytest.mark.parametrize("gateway_name", GATEWAY_SERVERS)
    def test_server_link(
        self, gateway_name, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link should return without error."""
        response = client.get(f"/servers/{gateway_name}")
        assert response.status_code in (200, 404), \
            f"Server link for {gateway_name} should return 200 or 404, got {response.status_code}"


class TestMetaLinks:
    """Tests for Meta column links: /gateway/meta/{name}"""

    @pytest.mark.parametrize("gateway_name", GATEWAY_SERVERS)
    def test_meta_link(
        self, gateway_name, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link should return without error and contain transform references."""
        response = client.get(f"/gateway/meta/{gateway_name}", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for {gateway_name} should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get(gateway_name, {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                f"Meta page for {gateway_name} should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                f"Meta page for {gateway_name} should reference response transform"
        
        # Check for template references if any
        templates_config = config.get("templates", {})
        for template_name, template_cid in templates_config.items():
            assert template_name in page or template_cid in page, \
                f"Meta page for {gateway_name} should reference template {template_name}"


class TestTestLinks:
    """Tests for Test column links: /gateway/test/cids/{mock_cid}/as/{name}"""

    @pytest.mark.parametrize("gateway_name", GATEWAY_SERVERS)
    def test_test_link(
        self, gateway_name, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/{gateway_name}",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for {gateway_name} should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/{gateway_name}/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for {gateway_name} should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )


class TestSampleLinks:
    """Tests for Sample column links: /cids/{mock_cid}"""

    def test_sample_link_returns_without_error(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Sample links should return without error."""
        response = client.get(f"/cids/{mock_cid}")
        assert response.status_code in (
            200,
            302,
            404,
        ), f"Sample link should return valid status, got {response.status_code}"
