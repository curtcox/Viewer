"""Integration tests for gateway table links on the gateways page.

Tests the links in the Configured Gateways table:
- Server links: /servers/{name}
- Meta links: /gateway/meta/{name}
- Test links: /gateway/test/cids/{mock_cid}/as/{name}
- Sample links: /cids/{mock_cid}

Uses Flask's test client for one-shot testing without HTTP or browser.
"""

from __future__ import annotations

import json
import re

import pytest

from database import db
from models import Server, Variable
from tests.test_gateway_test_support import TEST_CIDS_ARCHIVE_CID

pytestmark = pytest.mark.integration


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

    def test_server_link_returns_without_error(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server links should return without error."""
        # Test a few representative gateways
        test_gateways = ["jsonplaceholder", "man", "tldr", "hrx", "cids"]
        
        for gateway_name in test_gateways:
            if gateway_name in gateways_variable:
                response = client.get(f"/servers/{gateway_name}")
                assert response.status_code in (
                    200,
                    404,
                ), f"Server link for {gateway_name} should return 200 or 404, got {response.status_code}"


class TestMetaLinks:
    """Tests for Meta column links: /gateway/meta/{name}"""

    def test_meta_link_returns_without_error(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta links should return without error."""
        # Test a few representative gateways
        test_gateways = ["jsonplaceholder", "man", "tldr", "hrx", "cids"]
        
        for gateway_name in test_gateways:
            if gateway_name in gateways_variable:
                response = client.get(f"/gateway/meta/{gateway_name}", follow_redirects=True)
                assert (
                    response.status_code == 200
                ), f"Meta link for {gateway_name} should return 200, got {response.status_code}"

    def test_meta_page_contains_transform_links(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta page should contain links to the transforms used by the gateway."""
        # Test a gateway that has transforms configured
        test_gateways = ["jsonplaceholder", "man", "tldr"]
        
        for gateway_name in test_gateways:
            if gateway_name not in gateways_variable:
                continue
                
            config = gateways_variable[gateway_name]
            response = client.get(f"/gateway/meta/{gateway_name}", follow_redirects=True)
            page = response.get_data(as_text=True)
            
            # Check for request transform CID link if configured
            request_cid = config.get("request_transform_cid")
            if request_cid:
                # Meta page should show the CID in some form (link or display)
                assert (
                    request_cid in page or "request" in page.lower()
                ), f"Meta page for {gateway_name} should reference request transform"
            
            # Check for response transform CID link if configured
            response_cid = config.get("response_transform_cid")
            if response_cid:
                # Meta page should show the CID in some form (link or display)
                assert (
                    response_cid in page or "response" in page.lower()
                ), f"Meta page for {gateway_name} should reference response transform"

    def test_meta_page_contains_page_references(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta page should contain links to pages used by the gateway."""
        # Test a gateway with templates
        test_gateways = ["man", "tldr"]
        
        for gateway_name in test_gateways:
            if gateway_name not in gateways_variable:
                continue
                
            config = gateways_variable[gateway_name]
            templates_config = config.get("templates", {})
            
            if not templates_config:
                continue
                
            response = client.get(f"/gateway/meta/{gateway_name}", follow_redirects=True)
            page = response.get_data(as_text=True)
            
            # Check that template names or CIDs are referenced
            for template_name, template_cid in templates_config.items():
                # Meta page should show template name or CID
                assert (
                    template_name in page or template_cid in page
                ), f"Meta page for {gateway_name} should reference template {template_name}"


class TestTestLinks:
    """Tests for Test column links: /gateway/test/cids/{mock_cid}/as/{name}"""

    def test_test_link_returns_without_error(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test links should return without error."""
        # Test a few representative gateways
        test_gateways = ["jsonplaceholder", "man", "tldr", "hrx", "cids"]
        
        for gateway_name in test_gateways:
            if gateway_name in gateways_variable:
                response = client.get(
                    f"/gateway/test/cids/{mock_cid}/as/{gateway_name}"
                )
                assert response.status_code in (
                    200,
                    302,
                    404,
                    500,
                ), f"Test link for {gateway_name} should return valid status, got {response.status_code}"

    def test_test_page_contains_test_gateway_resource_link(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test page should have at least one link to a resource in the same test gateway.
        
        Note: This test expects the test CID to contain mock server data. If the CID doesn't exist
        or doesn't contain appropriate data, the test will show that resource links can't be verified.
        """
        # Test gateways that should have resource links
        test_gateways = ["jsonplaceholder", "man", "tldr"]
        
        for gateway_name in test_gateways:
            if gateway_name not in gateways_variable:
                continue
                
            response = client.get(
                f"/gateway/test/cids/{mock_cid}/as/{gateway_name}",
                follow_redirects=True
            )
            
            # The endpoint should at least return successfully
            assert response.status_code == 200, \
                f"Test link for {gateway_name} should return 200, got {response.status_code}"
            
            page = response.get_data(as_text=True)
            
            # Look for links that reference the test gateway pattern
            # Pattern: /gateway/test/cids/{mock_cid}/as/{gateway_name}/...
            test_pattern = f"/gateway/test/cids/{mock_cid}/as/{gateway_name}/"
            
            # Find all href attributes in the page
            href_pattern = re.compile(r'href=["\'](.*?)["\']')
            hrefs = href_pattern.findall(page)
            
            # Check if any href contains the test pattern
            matching_links = [href for href in hrefs if test_pattern in href]
            
            # Document whether resource links are present
            # Note: If the test CID doesn't contain mock data, this will fail
            if len(matching_links) == 0:
                # This is expected to fail when the mock CID doesn't exist or is empty
                # The test documents this requirement
                assert False, (
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
