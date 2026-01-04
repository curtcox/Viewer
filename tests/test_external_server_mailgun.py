"""Tests for the Mailgun server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import mailgun


def test_missing_api_key_returns_auth_error():
    result = mailgun.main(MAILGUN_API_KEY="", MAILGUN_DOMAIN="mg.example.com", dry_run=False)
    assert "error" in result["output"]


def test_missing_domain_returns_auth_error():
    result = mailgun.main(MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = mailgun.main(operation="invalid_op", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=True)
    assert "error" in result["output"]


def test_send_message_requires_all_fields():
    result = mailgun.main(operation="send_message", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=True)
    assert "error" in result["output"]


def test_validate_email_requires_email():
    result = mailgun.main(operation="validate_email", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_send_message():
    result = mailgun.main(operation="send_message", to_email="to@example.com", from_email="from@example.com", subject="Test", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "messages" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_events():
    result = mailgun.main(operation="list_events", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "events" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = mailgun.main(operation="list_events", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.text = "not json"
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = mailgun.main(operation="list_events", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"id": "123", "event": "delivered"}]}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = mailgun.main(operation="list_events", MAILGUN_API_KEY="test_key", MAILGUN_DOMAIN="mg.example.com", dry_run=False, client=mock_client)
    assert "items" in result["output"]
    assert result["output"]["items"][0]["id"] == "123"
