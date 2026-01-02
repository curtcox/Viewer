"""Tests for the Apify server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import apify


def test_missing_api_key_returns_auth_error():
    result = apify.main(APIFY_API_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = apify.main(
        operation="invalid_op",
        APIFY_API_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_run_actor_validation():
    result = apify.main(
        operation="run_actor",
        APIFY_API_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "actor_id is required" in str(result["output"]).lower()

def test_get_run_validation():
    result = apify.main(
        operation="get_run",
        APIFY_API_TOKEN="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "run_id is required" in str(result["output"]).lower()




def test_dry_run_preview_for_list_actors():
    result = apify.main(
        operation="list_actors",
        APIFY_API_TOKEN="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "list_actors"

def test_dry_run_preview_for_run_actor():
    result = apify.main(
        operation="run_actor", actor_id="actor123",
        APIFY_API_TOKEN="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "run_actor"
    assert "actor_id" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.get.side_effect = requests.RequestException(response=mock_response)
    
    result = apify.main(
        operation="list_actors",
        APIFY_API_TOKEN="test_key",
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
    
    result = apify.main(
        operation="list_actors",
        APIFY_API_TOKEN="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
