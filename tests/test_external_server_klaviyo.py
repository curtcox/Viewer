"""Tests for the Klaviyo server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import klaviyo


def test_missing_api_key_returns_auth_error():
    result = klaviyo.main(KLAVIYO_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = klaviyo.main(
        operation="invalid_op", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_get_profile_requires_profile_id():
    result = klaviyo.main(
        operation="get_profile", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_create_profile_requires_email():
    result = klaviyo.main(
        operation="create_profile", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_get_list_requires_list_id():
    result = klaviyo.main(
        operation="get_list", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_create_list_requires_list_id():
    result = klaviyo.main(
        operation="create_list", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_add_profile_to_list_requires_both_ids():
    result = klaviyo.main(
        operation="add_profile_to_list", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_profiles():
    result = klaviyo.main(
        operation="list_profiles", KLAVIYO_API_KEY="test_key", dry_run=True
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "profiles" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_profile():
    result = klaviyo.main(
        operation="create_profile",
        email="test@example.com",
        first_name="John",
        KLAVIYO_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_list():
    result = klaviyo.main(
        operation="get_list",
        list_id="XyZ123",
        KLAVIYO_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "XyZ123" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = klaviyo.main(
        operation="list_profiles",
        KLAVIYO_API_KEY="test_key",
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

    result = klaviyo.main(
        operation="list_profiles",
        KLAVIYO_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_json():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "123", "type": "profile"}]}

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = klaviyo.main(
        operation="list_profiles",
        KLAVIYO_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "data" in result["output"]
    assert result["output"]["data"][0]["id"] == "123"


def test_invalid_json_in_properties_returns_error():
    result = klaviyo.main(
        operation="create_profile",
        email="test@example.com",
        properties="{invalid json}",
        KLAVIYO_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
