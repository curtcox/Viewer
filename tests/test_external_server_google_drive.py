"""Tests for the Google Drive server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import google_drive


def test_missing_credentials_returns_auth_error():
    result = google_drive.main(
        GOOGLE_SERVICE_ACCOUNT_JSON=None,
        GOOGLE_ACCESS_TOKEN=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_drive.main(
        operation="invalid_op",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_file_requires_file_id():
    result = google_drive.main(
        operation="get_file",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_upload_file_requires_file_name_and_content():
    result = google_drive.main(
        operation="upload_file",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_file_requires_file_id():
    result = google_drive.main(
        operation="delete_file",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_share_file_requires_file_id_and_email():
    result = google_drive.main(
        operation="share_file",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_files():
    result = google_drive.main(
        operation="list_files",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "www.googleapis.com/drive" in result["output"]["url"]


def test_dry_run_returns_preview_for_upload_file():
    result = google_drive.main(
        operation="upload_file",
        file_name="test.txt",
        file_content="Hello, World!",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_share_file():
    result = google_drive.main(
        operation="share_file",
        file_id="abc123",
        email="user@example.com",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = google_drive.main(
        operation="list_files",
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

    result = google_drive.main(
        operation="list_files",
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

    result = google_drive.main(
        operation="list_files",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_delete_file_success_returns_message():
    mock_response = Mock()
    mock_response.status_code = 204
    mock_response.ok = True

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_drive.main(
        operation="delete_file",
        file_id="abc123",
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
        "files": [{"id": "123", "name": "test.txt"}],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_drive.main(
        operation="list_files",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "files" in result["output"]
