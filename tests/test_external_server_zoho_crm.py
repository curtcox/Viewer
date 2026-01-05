"""Tests for the Zoho CRM server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import zoho_crm


def test_missing_access_token_returns_auth_error():
    result = zoho_crm.main(ZOHO_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = zoho_crm.main(operation="invalid_op", ZOHO_ACCESS_TOKEN="test-token")
    assert "error" in result["output"]


def test_invalid_module_returns_validation_error():
    result = zoho_crm.main(
        module="InvalidModule", ZOHO_ACCESS_TOKEN="test-token"
    )
    assert "error" in result["output"]


def test_get_record_requires_record_id():
    result = zoho_crm.main(
        operation="get_record",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_record_requires_data():
    result = zoho_crm.main(
        operation="create_record",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_record_requires_id_and_data():
    result = zoho_crm.main(
        operation="update_record",
        module="Accounts",
        record_id="123456",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_record_requires_record_id():
    result = zoho_crm.main(
        operation="delete_record",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_search_records_requires_criteria():
    result = zoho_crm.main(
        operation="search_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_records():
    result = zoho_crm.main(
        operation="list_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_create_record():
    result = zoho_crm.main(
        operation="create_record",
        module="Accounts",
        data={"Account_Name": "Test Company"},
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = zoho_crm.main(
        operation="list_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 200
    mock_response.text = "Not JSON"

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = zoho_crm.main(
        operation="list_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "code": "INVALID_TOKEN",
        "message": "Invalid OAuth token",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = zoho_crm.main(
        operation="list_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "data": [
            {"id": "123456", "Account_Name": "Company 1"},
            {"id": "789012", "Account_Name": "Company 2"},
        ],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = zoho_crm.main(
        operation="list_records",
        module="Accounts",
        ZOHO_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "data" in result["output"]
