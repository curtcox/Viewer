"""Tests for the Calendly server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import calendly


def test_missing_api_key_returns_auth_error():
    result = calendly.main(CALENDLY_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = calendly.main(operation="invalid_op", CALENDLY_API_KEY="test-key")
    assert "error" in result["output"]


def test_list_event_types_requires_user_uri():
    result = calendly.main(
        operation="list_event_types",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_event_type_requires_uuid():
    result = calendly.main(
        operation="get_event_type",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_events_requires_user_uri():
    result = calendly.main(
        operation="list_events",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_event_requires_uuid():
    result = calendly.main(
        operation="get_event",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_invitees_requires_event_uuid():
    result = calendly.main(
        operation="list_invitees",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_invitee_requires_uuid():
    result = calendly.main(
        operation="get_invitee",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_cancel_event_requires_uuid():
    result = calendly.main(
        operation="cancel_event",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_get_user():
    result = calendly.main(
        operation="get_user",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_cancel_event():
    result = calendly.main(
        operation="cancel_event",
        event_uuid="XXXXXX",
        CALENDLY_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = calendly.main(
        operation="get_user",
        CALENDLY_API_KEY="test-key",
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

    result = calendly.main(
        operation="get_user",
        CALENDLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "title": "Unauthenticated",
        "message": "The access token is invalid",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = calendly.main(
        operation="get_user",
        CALENDLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_cancel_success_returns_success():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 201

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = calendly.main(
        operation="cancel_event",
        event_uuid="XXXXXX",
        CALENDLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "resource": {
            "uri": "https://api.calendly.com/users/XXXXXX",
            "name": "John Doe",
            "email": "john@example.com",
        }
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = calendly.main(
        operation="get_user",
        CALENDLY_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "resource" in result["output"]
