"""Integration tests for gateway server functionality."""

from __future__ import annotations

import pytest

from database import db
from models import Server, Variable

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
    import json

    gateways_config = {
        "jsonplaceholder": {
            "description": "JSONPlaceholder fake REST API for testing",
            "request_transform_cid": "",
            "response_transform_cid": "",
        },
        "test-api": {
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


def test_gateway_instruction_page_has_link_table_columns(
    client,
    integration_app,
    gateway_server,
):
    """Gateway instruction page should include the link table headers."""
    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Server" in page
    assert "Gateway" in page
    assert "Meta" in page
    assert "Test" in page
    assert "External API" in page


def test_gateway_instruction_page_includes_links_for_builtin_gateways(
    client,
    integration_app,
    gateway_server,
):
    """Gateway instruction page should include links for gateways loaded from gateways.source.json."""
    import json

    from pathlib import Path

    from cid_core import generate_cid
    from tests.test_gateway_test_support import TEST_CIDS_ARCHIVE_CID, TEST_HRX_ARCHIVE_CID

    with open(
        "reference/templates/gateways.source.json", "r", encoding="utf-8"
    ) as f:
        gateways_config = json.load(f)

    with integration_app.app_context():
        variable = Variable(
            name="gateways",
            definition=json.dumps(gateways_config),
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()

    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)

    def expected_mock_cid(server_name: str) -> str:
        archive = Path("reference/files") / f"{server_name}.cids"
        if archive.exists():
            return generate_cid(archive.read_bytes())
        return TEST_CIDS_ARCHIVE_CID

    assert "/gateway/test/cids/" in page
    assert "/cids/" in page
    assert f"/gateway/test/cids/{TEST_HRX_ARCHIVE_CID}/as/" not in page
    assert f"/cids/{TEST_HRX_ARCHIVE_CID}" not in page

    # Non-external (internal-only) gateways
    for server_name in ("man", "tldr", "hrx", "cids"):
        mock_server_cid = expected_mock_cid(server_name)
        assert f"/servers/{server_name}" in page
        assert f"/gateway/{server_name}" in page
        assert f"/gateway/meta/{server_name}" in page

        # Table includes a test pattern link that uses a mock CID (no external API)
        assert (
            f"/gateway/test/cids/{mock_server_cid}/as/{server_name}" in page
        )


def test_gateways_page_redirects_to_gateway_home(
    client,
    integration_app,
    gateway_server,
):
    """/gateways should return the gateway home page content."""
    response = client.get("/gateways", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Gateway Server" in page


def test_gateway_instruction_page_includes_external_service_servers(
    client,
    integration_app,
    gateway_server,
):
    """Gateway instruction page should include archived external-service servers."""
    import json

    with open(
        "reference/templates/gateways.source.json", "r", encoding="utf-8"
    ) as f:
        gateways_config = json.load(f)

    with integration_app.app_context():
        variable = Variable(
            name="gateways",
            definition=json.dumps(gateways_config),
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()

    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)

    # Representative external-service servers backed by reference/archive/cids
    assert "/servers/github" in page
    assert "/servers/stripe" in page

    # External API labels should be present when the definition includes a URL
    assert "GitHub API" in page
    assert 'href="https://api.github.com"' in page


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


def test_gateway_configured_gateways_server_meta_test_links_respond_without_error(
    client,
    integration_app,
    gateway_server,
):
    """All Server/Meta/Test link targets in the Configured Gateways table should work locally.

    This uses Flask's test client (one-shot) and does not involve a browser or
    outbound HTTP requests.
    """

    import json
    from pathlib import Path

    from cid_core import generate_cid
    from cid_storage import ensure_cid_exists
    from reference.templates.servers import get_server_templates

    with open(
        "reference/templates/gateways.source.json", "r", encoding="utf-8"
    ) as f:
        gateways_config = json.load(f)

    with integration_app.app_context():
        existing = (
            db.session.query(Variable)
            .filter_by(name="gateways")
            .one_or_none()
        )
        if existing is None:
            db.session.add(
                Variable(
                    name="gateways",
                    definition=json.dumps(gateways_config),
                    enabled=True,
                )
            )

        templates = get_server_templates()
        template_def_by_id = {t.get("id"): t.get("definition") for t in templates}

        for server_name in gateways_config.keys():
            if db.session.query(Server).filter_by(name=server_name).first():
                continue

            definition = template_def_by_id.get(server_name)
            if not definition:
                # Keep the test strict: if the link exists but server isn't available
                # from templates, this should surface as a failure when requesting /servers/<name>.
                continue

            db.session.add(
                Server(
                    name=server_name,
                    definition=definition,
                    enabled=True,
                )
            )

        db.session.commit()

    # Confirm the configured gateways table renders.
    response = client.get("/gateway", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Configured Gateways" in page

    from tests.test_gateway_test_support import TEST_CIDS_ARCHIVE_CID

    def expected_mock_cid(server_name: str) -> str:
        archive = Path("reference/files") / f"{server_name}.cids"
        if archive.exists():
            content_bytes = archive.read_bytes()
            cid_value = generate_cid(content_bytes)
            with integration_app.app_context():
                ensure_cid_exists(cid_value, content_bytes)
            return cid_value

        cid_file = Path("cids") / TEST_CIDS_ARCHIVE_CID
        if cid_file.exists():
            with integration_app.app_context():
                ensure_cid_exists(TEST_CIDS_ARCHIVE_CID, cid_file.read_bytes())
        return TEST_CIDS_ARCHIVE_CID

    # Verify each Server/Meta/Test target responds without error.
    for server_name in gateways_config.keys():
        mock_server_cid = expected_mock_cid(server_name)
        server_url = f"/servers/{server_name}"
        meta_url = f"/gateway/meta/{server_name}"
        test_url = f"/gateway/test/cids/{mock_server_cid}/as/{server_name}"

        assert f'href="{server_url}"' in page
        assert f'href="{meta_url}"' in page
        assert f'href="{test_url}"' in page

        server_response = client.get(server_url, follow_redirects=True)
        assert server_response.status_code == 200

        meta_response = client.get(meta_url, follow_redirects=True)
        assert meta_response.status_code == 200

        test_response = client.get(test_url, follow_redirects=True)
        assert test_response.status_code == 200


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


def test_gateway_meta_page_lists_templates_referenced_by_transform(
    client,
    integration_app,
    gateway_server,
):
    """Meta page should list templates referenced by resolve_template calls, even if not configured."""
    import json

    request_transform_source = """
def transform_request(request_details: dict, context: dict) -> dict:
    resolve_template = context.get("resolve_template")
    if resolve_template:
        resolve_template("man_error.html")
    return {"method": "GET"}
""".lstrip()

    response_transform_source = """
def transform_response(response_details: dict, context: dict) -> dict:
    resolve_template = context.get("resolve_template")
    if resolve_template:
        resolve_template("man_page.html")
    return {"output": "ok", "content_type": "text/plain"}
""".lstrip()

    request_cid = _create_transform_cid(integration_app, request_transform_source)
    response_cid = _create_transform_cid(integration_app, response_transform_source)

    gateways_config = {
        "jsonplaceholder": {
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

    response = client.get("/gateway/meta/jsonplaceholder", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Templates" in page
    assert "man_error.html" in page
    assert "man_page.html" in page
    assert "Missing Mapping" in page


def test_gateway_returns_error_when_response_transform_missing(
    client,
    integration_app,
    gateway_server,
):
    """Gateway should return an error page when a configured response transform cannot be loaded."""
    import json

    gateways_config = {
        "jsonplaceholder": {
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

    response = client.get("/gateway/jsonplaceholder/posts/1", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    # Gateway should show an error page (either for missing transform or missing target)
    assert "Gateway Error" in page
    assert ("Response Transform Not Found" in page or "No internal target" in page or "error" in page.lower())


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


def test_gateway_meta_page_shows_templates_section(
    client,
    integration_app,
    gateway_server,
):
    """Meta page should show templates section when templates are configured."""
    import json
    from cid_storage import store_cid_from_bytes

    # Create a simple template
    template_content = b"<html><body>{{ test }}</body></html>"
    template_cid = store_cid_from_bytes(template_content)

    # Create gateway config with templates
    gateways_config = {
        "test-gateway": {
            "description": "Test gateway with templates",
            "response_transform_cid": "",
            "templates": {
                "test.html": template_cid,
            },
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

    # Visit meta page
    response = client.get("/gateway/meta/test-gateway", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show Templates section
    assert "Templates" in page
    assert "test.html" in page
    assert "Valid" in page or "valid" in page


def test_gateway_meta_page_shows_template_variables(
    client,
    integration_app,
    gateway_server,
):
    """Meta page should show detected template variables."""
    import json
    from cid_storage import store_cid_from_bytes

    # Create a template with variables
    template_content = b"<html><body>{{ command }} - {{ message }}</body></html>"
    template_cid = store_cid_from_bytes(template_content)

    # Create gateway config with templates
    gateways_config = {
        "test-vars": {
            "description": "Test gateway",
            "response_transform_cid": "",
            "templates": {
                "page.html": template_cid,
            },
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

    # Visit meta page
    response = client.get("/gateway/meta/test-vars", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show detected variables
    assert "command" in page
    assert "message" in page


def test_gateway_meta_page_shows_no_templates_message(
    client,
    integration_app,
    gateway_server,
):
    """Meta page should show message when no templates configured."""
    import json

    # Create gateway config without templates
    gateways_config = {
        "no-templates": {
            "description": "Gateway without templates",
            "response_transform_cid": "FAKE_CID",
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

    # Visit meta page
    response = client.get("/gateway/meta/no-templates", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show no templates message
    assert "No templates configured" in page or "no templates" in page.lower()


def test_gateway_template_validation_error(
    client,
    integration_app,
    gateway_server,
):
    """Meta page should show error for invalid template."""
    import json

    # Create gateway config with invalid template CID
    gateways_config = {
        "bad-template": {
            "description": "Gateway with bad template",
            "response_transform_cid": "",
            "templates": {
                "broken.html": "INVALID_CID_THAT_DOES_NOT_EXIST",
            },
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

    # Visit meta page
    response = client.get("/gateway/meta/bad-template", follow_redirects=True)
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    # Should show error status
    assert "Error" in page or "error" in page.lower()
    assert "broken.html" in page
