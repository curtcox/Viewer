"""Tests for the FreshBooks server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import freshbooks


def test_missing_access_token_returns_auth_error():
    result = freshbooks.main(FRESHBOOKS_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = freshbooks.main(
        operation="invalid_op",
        endpoint="invoices",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_missing_endpoint_returns_validation_error():
    result = freshbooks.main(
        operation="list",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "endpoint" in result["output"]["error"]["message"].lower()


def test_get_operation_requires_entity_id():
    result = freshbooks.main(
        operation="get",
        endpoint="clients",
        business_id="12345",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_operation_requires_data():
    result = freshbooks.main(
        operation="create",
        endpoint="clients",
        business_id="12345",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_operation_requires_entity_id_and_data():
    result = freshbooks.main(
        operation="update",
        endpoint="clients",
        business_id="12345",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_operation_requires_entity_id():
    result = freshbooks.main(
        operation="delete",
        endpoint="clients",
        business_id="12345",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list():
    result = freshbooks.main(
        operation="list",
        endpoint="invoices",
        business_id="12345",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "12345" in result["output"]["url"]
    assert "invoices" in result["output"]["url"]


def test_dry_run_returns_preview_for_get():
    result = freshbooks.main(
        operation="get",
        endpoint="clients",
        business_id="12345",
        entity_id="67890",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "67890" in result["output"]["url"]


def test_dry_run_returns_preview_for_create():
    result = freshbooks.main(
        operation="create",
        endpoint="clients",
        business_id="12345",
        data='{"organization": "Test Corp"}',
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]
    assert result["output"]["payload"]["organization"] == "Test Corp"


def test_dry_run_returns_preview_for_update():
    result = freshbooks.main(
        operation="update",
        endpoint="clients",
        business_id="12345",
        entity_id="67890",
        data='{"organization": "Updated Corp"}',
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "PUT"
    assert "67890" in result["output"]["url"]


def test_dry_run_returns_preview_for_delete():
    result = freshbooks.main(
        operation="delete",
        endpoint="clients",
        business_id="12345",
        entity_id="67890",
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "DELETE"
    assert "67890" in result["output"]["url"]


def test_query_params_are_parsed():
    result = freshbooks.main(
        operation="list",
        endpoint="invoices",
        business_id="12345",
        params='{"include[]": "lines"}',
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "params" in result["output"]
    assert "include[]" in result["output"]["params"]


def test_invalid_json_in_data_returns_error():
    result = freshbooks.main(
        operation="create",
        endpoint="clients",
        business_id="12345",
        data='{invalid json}',
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()


def test_invalid_json_in_params_returns_error():
    result = freshbooks.main(
        operation="list",
        endpoint="invoices",
        business_id="12345",
        params='{invalid json}',
        FRESHBOOKS_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()
