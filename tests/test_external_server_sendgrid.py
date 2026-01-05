"""Tests for the SendGrid server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import sendgrid


def test_missing_api_key_returns_auth_error():
    result = sendgrid.main(SENDGRID_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = sendgrid.main(operation="invalid_op", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_send_mail_requires_all_fields():
    result = sendgrid.main(operation="send_mail", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_template_requires_template_id():
    result = sendgrid.main(operation="get_template", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_contact_requires_contact_id():
    result = sendgrid.main(operation="get_contact", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_add_contact_requires_email():
    result = sendgrid.main(operation="add_contact", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_get_list_requires_list_id():
    result = sendgrid.main(operation="get_list", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_send_mail():
    result = sendgrid.main(operation="send_mail", to_email="to@example.com", from_email="from@example.com", subject="Test", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "mail/send" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_templates():
    result = sendgrid.main(operation="list_templates", SENDGRID_API_KEY="test_key", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "templates" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = sendgrid.main(operation="list_templates", SENDGRID_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.text = "not json"
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = sendgrid.main(operation="list_templates", SENDGRID_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"templates": [{"id": "abc", "name": "Test"}]}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = sendgrid.main(operation="list_templates", SENDGRID_API_KEY="test_key", dry_run=False, client=mock_client)
    assert "templates" in result["output"]
    assert result["output"]["templates"][0]["id"] == "abc"
