"""Tests for the Bitly server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import bitly


def test_missing_api_key_returns_auth_error():
    result = bitly.main(BITLY_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = bitly.main(
        operation="invalid_op",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_shorten_url_validation():
    result = bitly.main(
        operation="shorten_url",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "long_url is required" in str(result["output"]).lower()

def test_get_link_validation():
    result = bitly.main(
        operation="get_link",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "bitlink or link_id is required" in str(result["output"]).lower()




def test_dry_run_preview_for_shorten_url():
    result = bitly.main(
        operation="shorten_url", long_url="https://example.com",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "shorten_url"
    assert "long_url" in result["output"]

def test_dry_run_preview_for_get_link():
    result = bitly.main(
        operation="get_link", bitlink="bit.ly/abc",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_link"
    assert "bitlink" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.post.side_effect = requests.RequestException(response=mock_response)
    
    result = bitly.main(
        operation="shorten_url", long_url="https://example.com",
        BITLY_ACCESS_TOKEN="test_key",
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
    
    result = bitly.main(
        operation="shorten_url", long_url="https://example.com",
        BITLY_ACCESS_TOKEN="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
