"""Tests for the Clearbit server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import clearbit


def test_missing_api_key_returns_auth_error():
    result = clearbit.main(CLEARBIT_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = clearbit.main(
        operation="invalid_op",
        CLEARBIT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_enrich_company_validation():
    result = clearbit.main(
        operation="enrich_company",
        CLEARBIT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "domain is required" in str(result["output"]).lower()

def test_enrich_person_validation():
    result = clearbit.main(
        operation="enrich_person",
        CLEARBIT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "email is required" in str(result["output"]).lower()




def test_dry_run_preview_for_enrich_company():
    result = clearbit.main(
        operation="enrich_company", domain="example.com",
        CLEARBIT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "enrich_company"
    assert "domain" in result["output"]

def test_dry_run_preview_for_enrich_person():
    result = clearbit.main(
        operation="enrich_person", email="test@example.com",
        CLEARBIT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "enrich_person"
    assert "email" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.get.side_effect = requests.RequestException(response=mock_response)
    
    result = clearbit.main(
        operation="enrich_company", domain="example.com",
        CLEARBIT_API_KEY="test_key",
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
    
    result = clearbit.main(
        operation="enrich_company", domain="example.com",
        CLEARBIT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
