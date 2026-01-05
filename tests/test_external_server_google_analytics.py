"""Tests for the Google Analytics server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import google_analytics


def test_missing_credentials_returns_auth_error():
    result = google_analytics.main(property_id="123", GOOGLE_SERVICE_ACCOUNT_JSON=None, GOOGLE_ACCESS_TOKEN=None, dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_analytics.main(operation="invalid", property_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_requires_property_id():
    result = google_analytics.main(operation="run_report", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview():
    result = google_analytics.main(operation="run_report", property_id="123", metrics="activeUsers", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "operation" in result["output"]
    assert "analyticsdata.googleapis.com" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = google_analytics.main(operation="run_report", property_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"rowCount": 10, "rows": []}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = google_analytics.main(operation="run_report", property_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "rowCount" in result["output"]
