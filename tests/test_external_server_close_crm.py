"""Tests for the Close CRM server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import close_crm


def test_missing_api_key_returns_auth_error():
    result = close_crm.main(CLOSE_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = close_crm.main(operation="invalid_op", CLOSE_API_KEY="test-key")
    assert "error" in result["output"]


def test_get_lead_requires_lead_id():
    result = close_crm.main(
        operation="get_lead",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_lead_requires_data():
    result = close_crm.main(
        operation="create_lead",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_lead_requires_id_and_data():
    result = close_crm.main(
        operation="update_lead",
        lead_id="lead_123",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_contact_requires_contact_id():
    result = close_crm.main(
        operation="get_contact",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_opportunity_requires_opportunity_id():
    result = close_crm.main(
        operation="get_opportunity",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_leads():
    result = close_crm.main(
        operation="list_leads",
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_create_lead():
    result = close_crm.main(
        operation="create_lead",
        data={"name": "Test Lead"},
        CLOSE_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = close_crm.main(
        operation="list_leads",
        CLOSE_API_KEY="test-key",
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

    result = close_crm.main(
        operation="list_leads",
        CLOSE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": "Authentication failed",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = close_crm.main(
        operation="list_leads",
        CLOSE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "data": [
            {"id": "lead_123", "name": "Lead 1"},
            {"id": "lead_456", "name": "Lead 2"},
        ],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = close_crm.main(
        operation="list_leads",
        CLOSE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "data" in result["output"]
