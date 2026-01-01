"""Tests for the MailerLite server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import mailerlite


def test_missing_api_key_returns_auth_error():
    result = mailerlite.main(MAILERLITE_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = mailerlite.main(operation="invalid_op", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_subscriber_requires_subscriber_id():
    result = mailerlite.main(operation="get_subscriber", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_create_subscriber_requires_email():
    result = mailerlite.main(operation="create_subscriber", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_update_subscriber_requires_subscriber_id():
    result = mailerlite.main(operation="update_subscriber", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_group_requires_group_id():
    result = mailerlite.main(operation="get_group", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_campaign_requires_campaign_id():
    result = mailerlite.main(operation="get_campaign", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_subscribers():
    result = mailerlite.main(operation="list_subscribers", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "subscribers" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_subscriber():
    result = mailerlite.main(operation="create_subscriber", email="test@example.com", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = mailerlite.main(operation="list_subscribers", MAILERLITE_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.text = "not json"
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = mailerlite.main(operation="list_subscribers", MAILERLITE_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "123", "email": "test@example.com"}]}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = mailerlite.main(operation="list_subscribers", MAILERLITE_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "data" in result["output"]
    assert result["output"]["data"][0]["id"] == "123"


def test_invalid_json_in_fields_returns_error():
    result = mailerlite.main(operation="create_subscriber", email="test@example.com", fields="{invalid json}", MAILERLITE_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]
