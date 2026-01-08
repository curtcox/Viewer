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

    def test_server_link_jsonplaceholder(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for jsonplaceholder should return without error."""
        response = client.get("/servers/jsonplaceholder")
        assert response.status_code in (200, 404), \
            f"Server link for jsonplaceholder should return 200 or 404, got {response.status_code}"

    def test_server_link_man(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for man should return without error."""
        response = client.get("/servers/man")
        assert response.status_code in (200, 404), \
            f"Server link for man should return 200 or 404, got {response.status_code}"

    def test_server_link_tldr(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for tldr should return without error."""
        response = client.get("/servers/tldr")
        assert response.status_code in (200, 404), \
            f"Server link for tldr should return 200 or 404, got {response.status_code}"

    def test_server_link_hrx(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for hrx should return without error."""
        response = client.get("/servers/hrx")
        assert response.status_code in (200, 404), \
            f"Server link for hrx should return 200 or 404, got {response.status_code}"

    def test_server_link_cids(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for cids should return without error."""
        response = client.get("/servers/cids")
        assert response.status_code in (200, 404), \
            f"Server link for cids should return 200 or 404, got {response.status_code}"

    def test_server_link_json_api(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for json_api should return without error."""
        response = client.get("/servers/json_api")
        assert response.status_code in (200, 404), \
            f"Server link for json_api should return 200 or 404, got {response.status_code}"

    def test_server_link_github(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for github should return without error."""
        response = client.get("/servers/github")
        assert response.status_code in (200, 404), \
            f"Server link for github should return 200 or 404, got {response.status_code}"

    def test_server_link_stripe(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for stripe should return without error."""
        response = client.get("/servers/stripe")
        assert response.status_code in (200, 404), \
            f"Server link for stripe should return 200 or 404, got {response.status_code}"

    def test_server_link_teams(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for teams should return without error."""
        response = client.get("/servers/teams")
        assert response.status_code in (200, 404), \
            f"Server link for teams should return 200 or 404, got {response.status_code}"

    def test_server_link_servicenow(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Server link for servicenow should return without error."""
        response = client.get("/servers/servicenow")
        assert response.status_code in (200, 404), \
            f"Server link for servicenow should return 200 or 404, got {response.status_code}"


class TestMetaLinks:
    """Tests for Meta column links: /gateway/meta/{name}"""

    def test_meta_link_jsonplaceholder(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for jsonplaceholder should return without error and contain transform references."""
        response = client.get("/gateway/meta/jsonplaceholder", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for jsonplaceholder should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("jsonplaceholder", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for jsonplaceholder should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for jsonplaceholder should reference response transform"

    def test_meta_link_man(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for man should return without error and contain transform/template references."""
        response = client.get("/gateway/meta/man", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for man should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("man", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for man should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for man should reference response transform"
        
        # Check for template references
        templates_config = config.get("templates", {})
        for template_name, template_cid in templates_config.items():
            assert template_name in page or template_cid in page, \
                f"Meta page for man should reference template {template_name}"

    def test_meta_link_tldr(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for tldr should return without error and contain transform/template references."""
        response = client.get("/gateway/meta/tldr", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for tldr should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("tldr", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for tldr should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for tldr should reference response transform"
        
        # Check for template references
        templates_config = config.get("templates", {})
        for template_name, template_cid in templates_config.items():
            assert template_name in page or template_cid in page, \
                f"Meta page for tldr should reference template {template_name}"

    def test_meta_link_hrx(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for hrx should return without error and contain transform references."""
        response = client.get("/gateway/meta/hrx", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for hrx should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("hrx", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for hrx should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for hrx should reference response transform"

    def test_meta_link_cids(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for cids should return without error and contain transform references."""
        response = client.get("/gateway/meta/cids", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for cids should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("cids", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for cids should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for cids should reference response transform"

    def test_meta_link_json_api(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for json_api should return without error and contain transform references."""
        response = client.get("/gateway/meta/json_api", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for json_api should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("json_api", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for json_api should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for json_api should reference response transform"

    def test_meta_link_github(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for github should return without error and contain transform references."""
        response = client.get("/gateway/meta/github", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for github should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("github", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for github should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for github should reference response transform"

    def test_meta_link_stripe(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for stripe should return without error and contain transform references."""
        response = client.get("/gateway/meta/stripe", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for stripe should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("stripe", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for stripe should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for stripe should reference response transform"

    def test_meta_link_teams(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for teams should return without error and contain transform references."""
        response = client.get("/gateway/meta/teams", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for teams should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("teams", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for teams should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for teams should reference response transform"

    def test_meta_link_servicenow(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Meta link for servicenow should return without error and contain transform references."""
        response = client.get("/gateway/meta/servicenow", follow_redirects=True)
        assert response.status_code == 200, \
            f"Meta link for servicenow should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        config = gateways_variable.get("servicenow", {})
        
        # Check for request transform CID link if configured
        request_cid = config.get("request_transform_cid")
        if request_cid:
            assert request_cid in page or "request" in page.lower(), \
                "Meta page for servicenow should reference request transform"
        
        # Check for response transform CID link if configured
        response_cid = config.get("response_transform_cid")
        if response_cid:
            assert response_cid in page or "response" in page.lower(), \
                "Meta page for servicenow should reference response transform"


class TestTestLinks:
    """Tests for Test column links: /gateway/test/cids/{mock_cid}/as/{name}"""

    def test_test_link_jsonplaceholder(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for jsonplaceholder should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/jsonplaceholder",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for jsonplaceholder should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/jsonplaceholder/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for jsonplaceholder should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_man(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for man should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/man",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for man should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/man/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for man should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_tldr(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for tldr should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/tldr",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for tldr should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/tldr/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for tldr should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_hrx(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for hrx should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/hrx",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for hrx should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/hrx/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for hrx should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_cids(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for cids should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/cids",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for cids should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/cids/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for cids should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_json_api(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for json_api should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/json_api",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for json_api should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/json_api/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for json_api should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_github(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for github should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/github",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for github should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/github/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for github should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_stripe(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for stripe should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/stripe",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for stripe should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/stripe/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for stripe should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_teams(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for teams should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/teams",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for teams should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/teams/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for teams should contain at least one link to a resource "
            f"in the test gateway (pattern: {test_pattern}), but found {len(matching_links)} matching links. "
            f"This likely means the test CID ({mock_cid}) doesn't exist or doesn't contain mock server data."
        )

    def test_test_link_servicenow(
        self, client, integration_app, gateway_server, gateways_variable, mock_cid
    ):
        """Test link for servicenow should return without error and contain resource links."""
        response = client.get(
            f"/gateway/test/cids/{mock_cid}/as/servicenow",
            follow_redirects=True
        )
        assert response.status_code == 200, \
            f"Test link for servicenow should return 200, got {response.status_code}"
        
        page = response.get_data(as_text=True)
        test_pattern = f"/gateway/test/cids/{mock_cid}/as/servicenow/"
        
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        hrefs = href_pattern.findall(page)
        matching_links = [href for href in hrefs if test_pattern in href]
        
        assert len(matching_links) > 0, (
            f"Test page for servicenow should contain at least one link to a resource "
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
