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
def cids_server(integration_app):
    """Create the cids server needed for gateway test mode (/cids/{cid})."""
    from reference.templates.servers import get_server_templates

    templates = get_server_templates()
    cids_template = next(t for t in templates if t.get("id") == "cids")
    cids_definition = cids_template["definition"]

    with integration_app.app_context():
        server = Server(
            name="cids",
            definition=cids_definition,
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()

    return cids_definition


@pytest.fixture
def gateways_variable(integration_app):
    """Create the gateways variable with test configuration."""
    # Load the actual gateways configuration
    with open("reference/templates/gateways.source.json", "r", encoding="utf-8") as f:
        gateways_config = json.load(f)

    for gateway_name in GATEWAY_SERVERS:
        gateways_config.setdefault(gateway_name, {})

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


@pytest.fixture
def mock_cid_record(integration_app, mock_cid):
    """Ensure the mock CID file is available via the DB-backed cid_storage layer."""
    from cid_storage import ensure_cid_exists

    cid_file = Path("cids") / mock_cid
    content_bytes = cid_file.read_bytes()

    with integration_app.app_context():
        ensure_cid_exists(mock_cid, content_bytes)

    return mock_cid


@pytest.fixture
def service_mock_cids() -> dict[str, str]:
    from cid_core import generate_cid

    files_dir = Path("reference/files")
    mock_cids: dict[str, str] = {}
    for archive_path in sorted(files_dir.glob("*.cids")):
        server_name = archive_path.stem
        if not server_name:
            continue
        mock_cids[server_name] = generate_cid(archive_path.read_bytes())
    return mock_cids


@pytest.fixture
def service_mock_cid_records(integration_app, service_mock_cids):
    """Store each service CIDS archive in the DB so /cids?archive=<cid> can resolve it."""
    from cid_storage import ensure_cid_exists

    files_dir = Path("reference/files")

    with integration_app.app_context():
        for service, cid_value in service_mock_cids.items():
            archive_path = files_dir / f"{service}.cids"
            if not archive_path.exists():
                continue
            ensure_cid_exists(cid_value, archive_path.read_bytes())

    return service_mock_cids


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
        self,
        gateway_name,
        client,
        integration_app,
        gateway_server,
        cids_server,
        gateways_variable,
        mock_cid,
        mock_cid_record,
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


class TestConfiguredGatewaysTableLinks:
    """Validate the /gateway Configured Gateways table Test/Sample links."""

    def test_gateway_instruction_page_test_links_return_html_with_links(
        self,
        client,
        integration_app,
        gateway_server,
        cids_server,
        gateways_variable,
        service_mock_cids,
        service_mock_cid_records,
    ):
        response = client.get("/gateway", follow_redirects=True)
        assert response.status_code == 200

        page = response.get_data(as_text=True)

        test_link_pattern = re.compile(
            r'href=["\"](/gateway/test/cids/([^/"\"]+)/as/([^/"\"]+))["\"]'
        )
        test_links = test_link_pattern.findall(page)
        assert test_links, "Expected at least one Test link on /gateway"

        for url, cid_value, server_name in test_links:
            # Ensure links use the service-specific archive CID.
            expected_cid = service_mock_cids.get(server_name)
            assert expected_cid, f"Missing computed mock CID for {server_name}"
            assert cid_value == expected_cid, (
                f"Test link for {server_name} should use its service-specific CID. "
                f"Expected {expected_cid}, got {cid_value}"
            )

            test_response = client.get(url, follow_redirects=True)
            assert test_response.status_code == 200, f"Test link {url} should return 200"
            content_type = test_response.headers.get("Content-Type", "")
            assert "text/html" in content_type, (
                f"Test link {url} should return HTML, got Content-Type={content_type!r}"
            )

            test_page = test_response.get_data(as_text=True)
            hrefs = re.findall(r'href=["\"][^"\"]+["\"]', test_page)
            assert hrefs, f"Test page for {server_name} should contain at least one link"

    def test_gateway_instruction_page_sample_links_use_service_specific_cids(
        self,
        client,
        integration_app,
        gateway_server,
        cids_server,
        gateways_variable,
        service_mock_cids,
        service_mock_cid_records,
    ):
        response = client.get("/gateway", follow_redirects=True)
        assert response.status_code == 200

        page = response.get_data(as_text=True)

        sample_link_pattern = re.compile(r'href=["\"](/cids/([^/"\"]+))["\"]')
        sample_links = sample_link_pattern.findall(page)
        assert sample_links, "Expected at least one Sample link on /gateway"

        sample_cids_by_service: dict[str, str] = {}
        for url, cid_value in sample_links:
            if cid_value not in service_mock_cids.values():
                continue
            # Determine service name from CID mapping.
            service = next((k for k, v in service_mock_cids.items() if v == cid_value), None)
            if service:
                sample_cids_by_service[service] = cid_value

        assert sample_cids_by_service, "Expected Sample links to include service-specific mock CIDs"

        for service, cid_value in sample_cids_by_service.items():
            assert cid_value == service_mock_cids.get(service)
