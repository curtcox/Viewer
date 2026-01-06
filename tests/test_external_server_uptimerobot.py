"""Tests for the UptimeRobot server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import uptimerobot


def test_missing_api_key_returns_auth_error():
    result = uptimerobot.main(UPTIMEROBOT_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = uptimerobot.main(
        operation="invalid_op",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_new_monitor_validation():
    result = uptimerobot.main(
        operation="new_monitor", url="https://example.com",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "friendly_name are required" in str(result["output"]).lower()

def test_delete_monitor_validation():
    result = uptimerobot.main(
        operation="delete_monitor",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "monitor_id is required" in str(result["output"]).lower()




def test_dry_run_preview_for_get_monitors():
    result = uptimerobot.main(
        operation="get_monitors",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_monitors"

def test_dry_run_preview_for_new_monitor():
    result = uptimerobot.main(
        operation="new_monitor", url="https://example.com", friendly_name="Test",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "new_monitor"
    assert "url" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.post.side_effect = requests.RequestException(response=mock_response)

    result = uptimerobot.main(
        operation="get_monitors",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"result": "success", "data": {"id": "123"}}
    mock_response.raise_for_status = Mock()
    mock_client.post.return_value = mock_response

    result = uptimerobot.main(
        operation="get_monitors",
        UPTIMEROBOT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
