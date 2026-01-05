"""Tests for the LinkedIn Ads server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import linkedin_ads


def test_missing_access_token_returns_auth_error():
    result = linkedin_ads.main(LINKEDIN_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = linkedin_ads.main(
        operation="invalid_op", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_account_requires_account_id():
    result = linkedin_ads.main(
        operation="get_account", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_campaigns_requires_account_id():
    result = linkedin_ads.main(
        operation="list_campaigns", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_campaign_requires_campaign_id():
    result = linkedin_ads.main(
        operation="get_campaign", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_create_campaign_requires_all_fields():
    result = linkedin_ads.main(
        operation="create_campaign", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_campaign_groups_requires_account_id():
    result = linkedin_ads.main(
        operation="list_campaign_groups",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_campaign_group_requires_campaign_group_id():
    result = linkedin_ads.main(
        operation="get_campaign_group",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_analytics_requires_campaign_id():
    result = linkedin_ads.main(
        operation="get_analytics", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_accounts():
    result = linkedin_ads.main(
        operation="list_accounts", LINKEDIN_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "adAccounts" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_campaign():
    result = linkedin_ads.main(
        operation="create_campaign",
        account_id="urn:li:sponsoredAccount:123456",
        name="Test Campaign",
        campaign_group_id="987654321",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_campaign():
    result = linkedin_ads.main(
        operation="get_campaign",
        campaign_id="123456789",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "123456789" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_campaigns():
    result = linkedin_ads.main(
        operation="list_campaigns",
        account_id="urn:li:sponsoredAccount:123456",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "adCampaigns" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = linkedin_ads.main(
        operation="list_accounts",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_json_parsing_error_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Not JSON"
    mock_client.request.return_value = mock_response

    result = linkedin_ads.main(
        operation="list_accounts",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "elements": [{"id": "123", "name": "Test Account"}]
    }
    mock_client.request.return_value = mock_response

    result = linkedin_ads.main(
        operation="list_accounts",
        LINKEDIN_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "elements" in result["output"]
