"""Tests for the Postmark server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import postmark


def test_missing_server_token_returns_auth_error():
    result = postmark.main(POSTMARK_SERVER_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = postmark.main(operation="invalid_op", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "error" in result["output"]


def test_send_email_requires_all_fields():
    result = postmark.main(operation="send_email", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "error" in result["output"]


def test_send_template_email_requires_template_id():
    result = postmark.main(operation="send_template_email", to_email="to@example.com", from_email="from@example.com", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "error" in result["output"]


def test_get_message_requires_message_id():
    result = postmark.main(operation="get_message", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "error" in result["output"]


def test_get_template_requires_template_id():
    result = postmark.main(operation="get_template", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_send_email():
    result = postmark.main(operation="send_email", to_email="to@example.com", from_email="from@example.com", subject="Test", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "email" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_templates():
    result = postmark.main(operation="list_templates", POSTMARK_SERVER_TOKEN="test_token", dry_run=True)
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "templates" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = postmark.main(operation="list_templates", POSTMARK_SERVER_TOKEN="test_token", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.text = "not json"
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = postmark.main(operation="list_templates", POSTMARK_SERVER_TOKEN="test_token", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"Templates": [{"TemplateId": 123, "Name": "Test"}]}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = postmark.main(operation="list_templates", POSTMARK_SERVER_TOKEN="test_token", dry_run=False, client=mock_client)
    assert "Templates" in result["output"]
    assert result["output"]["Templates"][0]["TemplateId"] == 123
