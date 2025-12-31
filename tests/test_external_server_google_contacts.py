"""Tests for the Google Contacts server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import google_contacts


def test_missing_credentials_returns_auth_error():
    result = google_contacts.main(
        GOOGLE_SERVICE_ACCOUNT_JSON=None,
        GOOGLE_ACCESS_TOKEN=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_contacts.main(
        operation="invalid_op",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_contact_requires_resource_name():
    result = google_contacts.main(
        operation="get_contact",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_contact_requires_given_name():
    result = google_contacts.main(
        operation="create_contact",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_contact_requires_resource_name():
    result = google_contacts.main(
        operation="update_contact",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_contact_requires_resource_name():
    result = google_contacts.main(
        operation="delete_contact",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_contacts():
    result = google_contacts.main(
        operation="list_contacts",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "people.googleapis.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_contact():
    result = google_contacts.main(
        operation="create_contact",
        given_name="John",
        family_name="Doe",
        email="john@example.com",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = google_contacts.main(
        operation="list_contacts",
        GOOGLE_ACCESS_TOKEN="test-token",
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

    result = google_contacts.main(
        operation="list_contacts",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": {"message": "Invalid request", "code": 400}
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_contacts.main(
        operation="list_contacts",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_delete_contact_success_returns_message():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.ok = True

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_contacts.main(
        operation="delete_contact",
        resource_name="people/abc123",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "message" in result["output"]
    assert "deleted successfully" in result["output"]["message"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "connections": [{"resourceName": "people/123", "names": [{"displayName": "John Doe"}]}],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_contacts.main(
        operation="list_contacts",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "connections" in result["output"]
