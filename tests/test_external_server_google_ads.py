"""Tests for the Google Ads server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import google_ads


def test_missing_credentials_returns_auth_error():
    result = google_ads.main(customer_id="123", GOOGLE_SERVICE_ACCOUNT_JSON=None, GOOGLE_ACCESS_TOKEN=None, GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=False)
    assert "error" in result["output"]


def test_missing_developer_token_returns_error():
    result = google_ads.main(customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN=None, dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_ads.main(operation="invalid", customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=True)
    assert "error" in result["output"]


def test_requires_customer_id():
    result = google_ads.main(operation="list_campaigns", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=True)
    assert "error" in result["output"]


def test_search_requires_query():
    result = google_ads.main(operation="search", customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview():
    result = google_ads.main(operation="list_campaigns", customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=True)
    assert "operation" in result["output"]
    assert "googleads.googleapis.com" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = google_ads.main(operation="list_campaigns", customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"results": [{"campaign": {"id": "1", "name": "Test"}}]}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = google_ads.main(operation="list_campaigns", customer_id="123", GOOGLE_ACCESS_TOKEN="test", GOOGLE_ADS_DEVELOPER_TOKEN="dev", dry_run=False, client=mock_client)
    assert "results" in result["output"]
