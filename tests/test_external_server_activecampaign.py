"""Tests for the ActiveCampaign server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import activecampaign


def test_missing_api_key_returns_auth_error():
    result = activecampaign.main(
        ACTIVECAMPAIGN_API_KEY="",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_missing_url_returns_auth_error():
    result = activecampaign.main(
        ACTIVECAMPAIGN_API_KEY="test_key", ACTIVECAMPAIGN_URL="", dry_run=False
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = activecampaign.main(
        operation="invalid_op",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_contact_requires_contact_id():
    result = activecampaign.main(
        operation="get_contact",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_contact_requires_email():
    result = activecampaign.main(
        operation="create_contact",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_contact_requires_contact_id():
    result = activecampaign.main(
        operation="update_contact",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_list_requires_list_id():
    result = activecampaign.main(
        operation="get_list",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_campaign_requires_campaign_id():
    result = activecampaign.main(
        operation="get_campaign",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_contacts():
    result = activecampaign.main(
        operation="list_contacts",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "contacts" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_contact():
    result = activecampaign.main(
        operation="create_contact",
        email="test@example.com",
        first_name="John",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_list():
    result = activecampaign.main(
        operation="get_list",
        list_id="1",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "/lists/1" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = activecampaign.main(
        operation="list_contacts",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.text = "not json"
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = activecampaign.main(
        operation="list_contacts",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"contacts": [{"id": "123", "email": "test@example.com"}]}

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = activecampaign.main(
        operation="list_contacts",
        ACTIVECAMPAIGN_API_KEY="test_key",
        ACTIVECAMPAIGN_URL="https://test.api-us1.com",
        dry_run=False,
        client=mock_client,
    )
    assert "contacts" in result["output"]
    assert result["output"]["contacts"][0]["id"] == "123"
