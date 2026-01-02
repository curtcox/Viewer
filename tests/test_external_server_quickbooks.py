"""Tests for the QuickBooks Online server definition."""

from reference_templates.servers.definitions import quickbooks


def test_missing_access_token_returns_auth_error():
    result = quickbooks.main(
        QUICKBOOKS_ACCESS_TOKEN="", QUICKBOOKS_REALM_ID="123", dry_run=False
    )
    assert "error" in result["output"]


def test_missing_realm_id_returns_validation_error():
    result = quickbooks.main(QUICKBOOKS_ACCESS_TOKEN="test_token", dry_run=False)
    assert "error" in result["output"]
    assert "realm_id" in result["output"]["error"]["message"].lower()


def test_invalid_operation_returns_validation_error():
    result = quickbooks.main(
        operation="invalid_op",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_query_operation_requires_query():
    result = quickbooks.main(
        operation="query",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_operation_requires_entity_type_and_id():
    result = quickbooks.main(
        operation="get",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_operation_requires_entity_type_and_data():
    result = quickbooks.main(
        operation="create",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_operation_requires_entity_type_and_data():
    result = quickbooks.main(
        operation="update",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_operation_requires_entity_type_and_id():
    result = quickbooks.main(
        operation="delete",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_query():
    result = quickbooks.main(
        operation="query",
        query="SELECT * FROM Customer",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "query" in result["output"]["url"]
    assert "SELECT * FROM Customer" in result["output"]["params"]["query"]


def test_dry_run_returns_preview_for_get():
    result = quickbooks.main(
        operation="get",
        entity_type="Invoice",
        entity_id="456",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "invoice/456" in result["output"]["url"].lower()


def test_dry_run_returns_preview_for_create():
    result = quickbooks.main(
        operation="create",
        entity_type="Customer",
        data='{"DisplayName": "Test Customer"}',
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]
    assert result["output"]["payload"]["DisplayName"] == "Test Customer"


def test_dry_run_returns_preview_for_update():
    result = quickbooks.main(
        operation="update",
        entity_type="Customer",
        data='{"Id": "1", "DisplayName": "Updated"}',
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert result["output"]["params"]["operation"] == "update"


def test_dry_run_returns_preview_for_delete():
    result = quickbooks.main(
        operation="delete",
        entity_type="Customer",
        entity_id="789",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert result["output"]["params"]["operation"] == "delete"
    assert result["output"]["payload"]["Id"] == "789"


def test_realm_id_parameter_overrides_secret():
    result = quickbooks.main(
        operation="query",
        query="SELECT * FROM Customer",
        realm_id="999",
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "999" in result["output"]["url"]
    assert "123" not in result["output"]["url"]


def test_invalid_json_in_data_returns_error():
    result = quickbooks.main(
        operation="create",
        entity_type="Customer",
        data='{invalid json}',
        QUICKBOOKS_ACCESS_TOKEN="test_token",
        QUICKBOOKS_REALM_ID="123",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()
