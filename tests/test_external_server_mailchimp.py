"""Tests for the Mailchimp server definition."""

from unittest.mock import Mock

import pytest
import requests

from reference_templates.servers.definitions import mailchimp


def test_missing_api_key_returns_auth_error():
    result = mailchimp.main(MAILCHIMP_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_api_key_format_returns_error():
    # Test with a key that doesn't have the datacenter format
    result = mailchimp.main(MAILCHIMP_API_KEY="invalidkey", dry_run=True)
    assert "error" in result["output"]
    assert "format" in result["output"]["error"].lower()


def test_invalid_operation_returns_validation_error():
    result = mailchimp.main(
        operation="invalid_op", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "error" in result["output"]


def test_get_list_requires_list_id():
    result = mailchimp.main(
        operation="get_list", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "error" in result["output"]


def test_add_member_requires_list_id_and_email():
    result = mailchimp.main(
        operation="add_member", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "error" in result["output"]


def test_get_member_requires_list_id_and_email():
    result = mailchimp.main(
        operation="get_member", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "error" in result["output"]


def test_get_campaign_requires_campaign_id():
    result = mailchimp.main(
        operation="get_campaign", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_lists():
    result = mailchimp.main(
        operation="list_lists", MAILCHIMP_API_KEY="key-us1", dry_run=True
    )
    assert "operation" in result["output"]
    assert "us1.api.mailchimp.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_add_member():
    result = mailchimp.main(
        operation="add_member",
        list_id="abc123",
        email="test@example.com",
        MAILCHIMP_API_KEY="key-us1",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_datacenter_extraction():
    result = mailchimp.main(
        operation="list_lists", MAILCHIMP_API_KEY="mykey-us10", dry_run=True
    )
    assert "us10.api.mailchimp.com" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = mailchimp.main(
        operation="list_lists",
        MAILCHIMP_API_KEY="key-us1",
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

    result = mailchimp.main(
        operation="list_lists",
        MAILCHIMP_API_KEY="key-us1",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "detail": "Invalid list ID",
        "status": 400,
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = mailchimp.main(
        operation="get_list",
        list_id="invalid",
        MAILCHIMP_API_KEY="key-us1",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "lists": [
            {"id": "abc123", "name": "My List"},
        ]
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = mailchimp.main(
        operation="list_lists",
        MAILCHIMP_API_KEY="key-us1",
        dry_run=False,
        client=mock_client,
    )
    assert "lists" in result["output"]
