"""Tests for the Microsoft Excel server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import microsoft_excel


def test_missing_credentials_returns_auth_error():
    result = microsoft_excel.main(
        MICROSOFT_ACCESS_TOKEN=None,
        MICROSOFT_TENANT_ID=None,
        MICROSOFT_CLIENT_ID=None,
        MICROSOFT_CLIENT_SECRET=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = microsoft_excel.main(
        operation="invalid_op",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_all_operations_require_item_id():
    result = microsoft_excel.main(
        operation="list_worksheets",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_range_requires_worksheet_and_range():
    result = microsoft_excel.main(
        operation="get_range",
        item_id="file123",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_range_requires_values():
    result = microsoft_excel.main(
        operation="update_range",
        item_id="file123",
        worksheet_name="Sheet1",
        range_address="A1:B2",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_table_requires_table_name_and_range():
    result = microsoft_excel.main(
        operation="create_table",
        item_id="file123",
        worksheet_name="Sheet1",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_worksheets():
    result = microsoft_excel.main(
        operation="list_worksheets",
        item_id="file123",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "graph.microsoft.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_update_range():
    result = microsoft_excel.main(
        operation="update_range",
        item_id="file123",
        worksheet_name="Sheet1",
        range_address="A1:B2",
        values='[[1, 2], [3, 4]]',
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "PATCH"


def test_list_worksheets_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [{"name": "Sheet1"}]}
    mock_client.get.return_value = mock_response

    result = microsoft_excel.main(
        operation="list_worksheets",
        item_id="file123",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "value" in result["output"]


def test_get_range_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"values": [[1, 2], [3, 4]]}
    mock_client.get.return_value = mock_response

    result = microsoft_excel.main(
        operation="get_range",
        item_id="file123",
        worksheet_name="Sheet1",
        range_address="A1:B2",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "values" in result["output"]


def test_update_range_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"values": [[5, 6], [7, 8]]}
    mock_client.patch.return_value = mock_response

    result = microsoft_excel.main(
        operation="update_range",
        item_id="file123",
        worksheet_name="Sheet1",
        range_address="A1:B2",
        values='[[5, 6], [7, 8]]',
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "values" in result["output"]


def test_invalid_json_values_returns_error():
    result = microsoft_excel.main(
        operation="update_range",
        item_id="file123",
        worksheet_name="Sheet1",
        range_address="A1:B2",
        values='invalid json',
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_api_error_handling():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Worksheet not found"}}
    mock_client.get.return_value = mock_response

    result = microsoft_excel.main(
        operation="list_worksheets",
        item_id="nonexistent",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_request_exception_handling():
    mock_client = Mock()
    mock_client.get.side_effect = requests.RequestException("Network error")

    result = microsoft_excel.main(
        operation="list_worksheets",
        item_id="file123",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]
