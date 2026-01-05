"""Tests for the Insightly server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import insightly


def test_missing_api_key_returns_auth_error():
    result = insightly.main(INSIGHTLY_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = insightly.main(operation="invalid_op", INSIGHTLY_API_KEY="test-key")
    assert "error" in result["output"]


def test_get_contact_requires_contact_id():
    result = insightly.main(
        operation="get_contact",
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_contact_requires_data():
    result = insightly.main(
        operation="create_contact",
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_contact_requires_id_and_data():
    result = insightly.main(
        operation="update_contact",
        contact_id=123,
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_organization_requires_org_id():
    result = insightly.main(
        operation="get_organization",
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_opportunity_requires_opportunity_id():
    result = insightly.main(
        operation="get_opportunity",
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_contacts():
    result = insightly.main(
        operation="list_contacts",
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_create_contact():
    result = insightly.main(
        operation="create_contact",
        data={"FIRST_NAME": "John", "LAST_NAME": "Doe"},
        INSIGHTLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = insightly.main(
        operation="list_contacts",
        INSIGHTLY_API_KEY="test-key",
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

    result = insightly.main(
        operation="list_contacts",
        INSIGHTLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": "Unauthorized",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = insightly.main(
        operation="list_contacts",
        INSIGHTLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [
        {"CONTACT_ID": 123, "FIRST_NAME": "John", "LAST_NAME": "Doe"},
        {"CONTACT_ID": 456, "FIRST_NAME": "Jane", "LAST_NAME": "Smith"},
    ]

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = insightly.main(
        operation="list_contacts",
        INSIGHTLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert isinstance(result["output"], list)
    assert len(result["output"]) == 2
