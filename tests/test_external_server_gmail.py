"""Tests for the Gmail server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import gmail


def test_missing_credentials_returns_auth_error():
    result = gmail.main(
        GOOGLE_SERVICE_ACCOUNT_JSON=None,
        GOOGLE_ACCESS_TOKEN=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = gmail.main(
        operation="invalid_op",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_message_requires_message_id():
    result = gmail.main(
        operation="get_message",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_send_message_requires_to_subject_body():
    result = gmail.main(
        operation="send_message",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_messages():
    result = gmail.main(
        operation="list_messages",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "gmail.googleapis.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_send_message():
    result = gmail.main(
        operation="send_message",
        to="test@example.com",
        subject="Test",
        body="Test body",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = gmail.main(
        operation="list_messages",
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

    result = gmail.main(
        operation="list_messages",
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

    result = gmail.main(
        operation="list_messages",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "messages": [{"id": "123", "threadId": "456"}],
        "resultSizeEstimate": 1,
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = gmail.main(
        operation="list_messages",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "messages" in result["output"]
