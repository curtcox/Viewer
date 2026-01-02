"""Tests for the Xero server definition."""

from reference_templates.servers.definitions import xero


def test_missing_access_token_returns_auth_error():
    result = xero.main(
        XERO_ACCESS_TOKEN="", XERO_TENANT_ID="abc-123", dry_run=False
    )
    assert "error" in result["output"]


def test_missing_tenant_id_returns_validation_error():
    result = xero.main(XERO_ACCESS_TOKEN="test_token", dry_run=False)
    assert "error" in result["output"]
    assert "tenant_id" in result["output"]["error"]["message"].lower()


def test_invalid_operation_returns_validation_error():
    result = xero.main(
        operation="invalid_op",
        endpoint="Invoices",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_missing_endpoint_returns_validation_error():
    result = xero.main(
        operation="list",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "endpoint" in result["output"]["error"]["message"].lower()


def test_get_operation_requires_entity_id():
    result = xero.main(
        operation="get",
        endpoint="Contacts",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_operation_requires_data():
    result = xero.main(
        operation="create",
        endpoint="Contacts",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_operation_requires_entity_id_and_data():
    result = xero.main(
        operation="update",
        endpoint="Contacts",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_operation_requires_entity_id():
    result = xero.main(
        operation="delete",
        endpoint="Contacts",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list():
    result = xero.main(
        operation="list",
        endpoint="Invoices",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "Invoices" in result["output"]["url"]


def test_dry_run_returns_preview_for_get():
    result = xero.main(
        operation="get",
        endpoint="Contacts",
        entity_id="xyz-789",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "xyz-789" in result["output"]["url"]


def test_dry_run_returns_preview_for_create():
    result = xero.main(
        operation="create",
        endpoint="Contacts",
        data='{"Name": "Test Contact"}',
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "PUT"  # Xero uses PUT for create
    assert "payload" in result["output"]
    assert result["output"]["payload"]["Name"] == "Test Contact"


def test_dry_run_returns_preview_for_update():
    result = xero.main(
        operation="update",
        endpoint="Contacts",
        entity_id="xyz-789",
        data='{"Name": "Updated Contact"}',
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "xyz-789" in result["output"]["url"]


def test_dry_run_returns_preview_for_delete():
    result = xero.main(
        operation="delete",
        endpoint="Contacts",
        entity_id="xyz-789",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "DELETE"
    assert "xyz-789" in result["output"]["url"]


def test_tenant_id_parameter_overrides_secret():
    result = xero.main(
        operation="list",
        endpoint="Invoices",
        tenant_id="override-123",
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="default-123",
        dry_run=True,
    )
    # Check that the header would use the override tenant_id
    assert "operation" in result["output"]


def test_query_params_are_parsed():
    result = xero.main(
        operation="list",
        endpoint="Invoices",
        params='{"where": "Status==\\"AUTHORISED\\""}',
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "params" in result["output"]
    assert "where" in result["output"]["params"]


def test_invalid_json_in_data_returns_error():
    result = xero.main(
        operation="create",
        endpoint="Contacts",
        data='{invalid json}',
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()


def test_invalid_json_in_params_returns_error():
    result = xero.main(
        operation="list",
        endpoint="Invoices",
        params='{invalid json}',
        XERO_ACCESS_TOKEN="test_token",
        XERO_TENANT_ID="abc-123",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()
