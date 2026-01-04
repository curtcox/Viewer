"""Tests for the Microsoft Teams server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import microsoft_teams


def test_missing_credentials_returns_auth_error():
    result = microsoft_teams.main(
        MICROSOFT_ACCESS_TOKEN=None,
        MICROSOFT_TENANT_ID=None,
        MICROSOFT_CLIENT_ID=None,
        MICROSOFT_CLIENT_SECRET=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = microsoft_teams.main(
        operation="invalid_op",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_team_requires_team_id():
    result = microsoft_teams.main(
        operation="get_team",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_send_message_requires_team_id_channel_id_message():
    result = microsoft_teams.main(
        operation="send_message",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_messages_requires_team_id_and_channel_id():
    result = microsoft_teams.main(
        operation="list_messages",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_teams():
    result = microsoft_teams.main(
        operation="list_teams",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "graph.microsoft.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_send_message():
    result = microsoft_teams.main(
        operation="send_message",
        team_id="team-123",
        channel_id="channel-456",
        message="Hello Teams!",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_list_teams_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [{"id": "team1", "displayName": "Test Team"}]}
    mock_client.get.return_value = mock_response

    result = microsoft_teams.main(
        operation="list_teams",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "value" in result["output"]


def test_get_team_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "team1", "displayName": "Test Team"}
    mock_client.get.return_value = mock_response

    result = microsoft_teams.main(
        operation="get_team",
        team_id="team1",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["id"] == "team1"


def test_send_message_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "msg1"}
    mock_client.post.return_value = mock_response

    result = microsoft_teams.main(
        operation="send_message",
        team_id="team1",
        channel_id="channel1",
        message="Test message",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "id" in result["output"]


def test_api_error_handling():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Team not found"}}
    mock_client.get.return_value = mock_response

    result = microsoft_teams.main(
        operation="get_team",
        team_id="nonexistent",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_request_exception_handling():
    mock_client = Mock()
    mock_client.get.side_effect = requests.RequestException("Network error")

    result = microsoft_teams.main(
        operation="list_teams",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]
