"""Tests for the Hunter.io server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import hunter


def test_missing_api_key_returns_auth_error():
    result = hunter.main(HUNTER_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = hunter.main(
        operation="invalid_op",
        HUNTER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_domain_search_validation():
    result = hunter.main(
        operation="domain_search",
        HUNTER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "domain is required" in str(result["output"]).lower()

def test_email_finder_validation():
    result = hunter.main(
        operation="email_finder", domain="example.com", first_name="John",
        HUNTER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "last_name are required" in str(result["output"]).lower()




def test_dry_run_preview_for_domain_search():
    result = hunter.main(
        operation="domain_search", domain="example.com",
        HUNTER_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "domain_search"
    assert "domain" in result["output"]

def test_dry_run_preview_for_email_verifier():
    result = hunter.main(
        operation="email_verifier", email="test@example.com",
        HUNTER_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "email_verifier"
    assert "email" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.get.side_effect = requests.RequestException(response=mock_response)
    
    result = hunter.main(
        operation="domain_search", domain="example.com",
        HUNTER_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"result": "success", "data": {"id": "123"}}
    mock_response.raise_for_status = Mock()
    mock_client.get.return_value = mock_response
    
    result = hunter.main(
        operation="domain_search", domain="example.com",
        HUNTER_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
