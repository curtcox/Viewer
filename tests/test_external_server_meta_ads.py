"""Tests for the Meta Ads server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import meta_ads


def test_missing_access_token_returns_auth_error():
    result = meta_ads.main(META_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = meta_ads.main(
        operation="invalid_op", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_campaigns_requires_account_id():
    result = meta_ads.main(
        operation="list_campaigns", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_campaign_requires_campaign_id():
    result = meta_ads.main(
        operation="get_campaign", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_create_campaign_requires_all_fields():
    result = meta_ads.main(
        operation="create_campaign", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_adsets_requires_account_id():
    result = meta_ads.main(
        operation="list_adsets", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_adset_requires_ad_set_id():
    result = meta_ads.main(
        operation="get_adset", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_ads_requires_account_id():
    result = meta_ads.main(
        operation="list_ads", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_ad_requires_ad_id():
    result = meta_ads.main(
        operation="get_ad", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_insights_requires_entity_id():
    result = meta_ads.main(
        operation="get_insights", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_accounts():
    result = meta_ads.main(
        operation="list_accounts", META_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "adaccounts" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_campaign():
    result = meta_ads.main(
        operation="create_campaign",
        account_id="act_123456789",
        campaign_name="Test Campaign",
        objective="OUTCOME_TRAFFIC",
        META_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_campaign():
    result = meta_ads.main(
        operation="get_campaign",
        campaign_id="120123456789",
        META_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "120123456789" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = meta_ads.main(
        operation="list_accounts",
        META_ACCESS_TOKEN="test_token",
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

    result = meta_ads.main(
        operation="list_accounts",
        META_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"data": [{"id": "act_123", "name": "Test"}]}
    mock_client.request.return_value = mock_response

    result = meta_ads.main(
        operation="list_accounts",
        META_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "data" in result["output"]
