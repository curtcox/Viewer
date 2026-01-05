"""Tests for the Pipedrive server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import pipedrive


def test_missing_api_token_returns_auth_error():
    result = pipedrive.main(PIPEDRIVE_API_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = pipedrive.main(
        operation="invalid_op", PIPEDRIVE_API_TOKEN="test-token"
    )
    assert "error" in result["output"]


def test_get_deal_requires_deal_id():
    result = pipedrive.main(
        operation="get_deal",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_deal_requires_data():
    result = pipedrive.main(
        operation="create_deal",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_deal_requires_id_and_data():
    result = pipedrive.main(
        operation="update_deal",
        deal_id=123,
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_person_requires_person_id():
    result = pipedrive.main(
        operation="get_person",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_organization_requires_org_id():
    result = pipedrive.main(
        operation="get_organization",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_deals():
    result = pipedrive.main(
        operation="list_deals",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_create_deal():
    result = pipedrive.main(
        operation="create_deal",
        data={"title": "Test Deal"},
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = pipedrive.main(
        operation="list_deals",
        PIPEDRIVE_API_TOKEN="test-token",
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

    result = pipedrive.main(
        operation="list_deals",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "success": False,
        "error": "Unauthorized",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = pipedrive.main(
        operation="list_deals",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "success": True,
        "data": [
            {"id": 1, "title": "Deal 1"},
            {"id": 2, "title": "Deal 2"},
        ],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = pipedrive.main(
        operation="list_deals",
        PIPEDRIVE_API_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "data" in result["output"]
