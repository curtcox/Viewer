"""Tests for the Zoom server definition."""

from unittest.mock import Mock

import pytest
import requests

from reference_templates.servers.definitions import zoom


def test_missing_token_returns_auth_error():
    result = zoom.main(ZOOM_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = zoom.main(
        operation="invalid_op", ZOOM_ACCESS_TOKEN="test-token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_meeting_requires_meeting_id():
    result = zoom.main(
        operation="get_meeting", ZOOM_ACCESS_TOKEN="test-token", dry_run=True
    )
    assert "error" in result["output"]


def test_create_meeting_requires_meeting_data():
    result = zoom.main(
        operation="create_meeting", ZOOM_ACCESS_TOKEN="test-token", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_meetings():
    result = zoom.main(
        operation="list_meetings", ZOOM_ACCESS_TOKEN="test-token", dry_run=True
    )
    assert "operation" in result["output"]
    assert "zoom.us" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_meeting():
    result = zoom.main(
        operation="create_meeting",
        meeting_data={"topic": "Test Meeting", "type": 2},
        ZOOM_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_default_user_id_is_me():
    result = zoom.main(
        operation="list_meetings", ZOOM_ACCESS_TOKEN="test-token", dry_run=True
    )
    assert "/users/me/" in result["output"]["url"]


def test_custom_user_id():
    result = zoom.main(
        operation="list_meetings",
        user_id="user123",
        ZOOM_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "/users/user123/" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = zoom.main(
        operation="list_meetings",
        ZOOM_ACCESS_TOKEN="test-token",
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

    result = zoom.main(
        operation="list_meetings",
        ZOOM_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "message": "Meeting not found",
        "code": 3001,
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = zoom.main(
        operation="get_meeting",
        meeting_id="invalid",
        ZOOM_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "meetings": [
            {"id": "123456789", "topic": "Test Meeting"},
        ]
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = zoom.main(
        operation="list_meetings",
        ZOOM_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "meetings" in result["output"]
