"""Tests for the Google Calendar server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import google_calendar


def test_missing_credentials_returns_auth_error():
    result = google_calendar.main(
        GOOGLE_SERVICE_ACCOUNT_JSON=None,
        GOOGLE_ACCESS_TOKEN=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_calendar.main(
        operation="invalid_op",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_event_requires_event_id():
    result = google_calendar.main(
        operation="get_event",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_event_requires_summary_and_times():
    result = google_calendar.main(
        operation="create_event",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_event_requires_event_id():
    result = google_calendar.main(
        operation="update_event",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_event_requires_event_id():
    result = google_calendar.main(
        operation="delete_event",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_events():
    result = google_calendar.main(
        operation="list_events",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "www.googleapis.com/calendar" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_event():
    result = google_calendar.main(
        operation="create_event",
        summary="Team Meeting",
        start_time="2025-01-15T10:00:00Z",
        end_time="2025-01-15T11:00:00Z",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = google_calendar.main(
        operation="list_events",
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

    result = google_calendar.main(
        operation="list_events",
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

    result = google_calendar.main(
        operation="list_events",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_delete_event_success_returns_message():
    mock_response = Mock()
    mock_response.status_code = 204
    mock_response.ok = True

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_calendar.main(
        operation="delete_event",
        event_id="abc123",
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
        "items": [{"id": "123", "summary": "Meeting"}],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = google_calendar.main(
        operation="list_events",
        GOOGLE_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "items" in result["output"]
