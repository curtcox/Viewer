"""Tests for the Microsoft Outlook server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import microsoft_outlook


def test_missing_credentials_returns_auth_error():
    result = microsoft_outlook.main(
        MICROSOFT_ACCESS_TOKEN=None,
        MICROSOFT_TENANT_ID=None,
        MICROSOFT_CLIENT_ID=None,
        MICROSOFT_CLIENT_SECRET=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = microsoft_outlook.main(
        operation="invalid_op",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_message_requires_message_id():
    result = microsoft_outlook.main(
        operation="get_message",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_send_message_requires_recipients_subject_body():
    result = microsoft_outlook.main(
        operation="send_message",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_message_requires_message_id():
    result = microsoft_outlook.main(
        operation="delete_message",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_messages():
    result = microsoft_outlook.main(
        operation="list_messages",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "graph.microsoft.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_send_message():
    result = microsoft_outlook.main(
        operation="send_message",
        to_recipients="user@example.com",
        subject="Test",
        body="Hello",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_list_messages_with_filter():
    result = microsoft_outlook.main(
        operation="list_messages",
        filter="isRead eq false",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "isRead eq false" in str(result["output"]["payload"])


def test_send_message_with_multiple_recipients():
    result = microsoft_outlook.main(
        operation="send_message",
        to_recipients="user1@example.com, user2@example.com",
        subject="Test",
        body="Hello",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert len(result["output"]["payload"]["message"]["toRecipients"]) == 2


def test_list_messages_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [{"id": "msg1", "subject": "Test"}]}
    mock_client.get.return_value = mock_response

    result = microsoft_outlook.main(
        operation="list_messages",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "value" in result["output"]
    assert len(result["output"]["value"]) == 1


def test_send_message_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 202
    mock_response.json.return_value = {}
    mock_client.post.return_value = mock_response

    result = microsoft_outlook.main(
        operation="send_message",
        to_recipients="user@example.com",
        subject="Test",
        body="Hello",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"] == {}


def test_delete_message_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 204
    mock_client.delete.return_value = mock_response

    result = microsoft_outlook.main(
        operation="delete_message",
        message_id="msg123",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_api_error_handling():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Not found"}}
    mock_client.get.return_value = mock_response

    result = microsoft_outlook.main(
        operation="get_message",
        message_id="nonexistent",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_request_exception_handling():
    mock_client = Mock()
    mock_client.get.side_effect = requests.RequestException("Network error")

    result = microsoft_outlook.main(
        operation="list_messages",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]
