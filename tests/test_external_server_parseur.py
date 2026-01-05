"""Tests for the Parseur server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import parseur


def test_missing_api_key_returns_auth_error():
    result = parseur.main(PARSEUR_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = parseur.main(
        operation="invalid_op",
        PARSEUR_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_get_inbox_validation():
    result = parseur.main(
        operation="get_inbox",
        PARSEUR_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "inbox_id is required" in str(result["output"]).lower()

def test_get_document_validation():
    result = parseur.main(
        operation="get_document", inbox_id="i123",
        PARSEUR_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "document_id is required" in str(result["output"]).lower()




def test_dry_run_preview_for_list_inboxes():
    result = parseur.main(
        operation="list_inboxes",
        PARSEUR_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "list_inboxes"

def test_dry_run_preview_for_get_inbox():
    result = parseur.main(
        operation="get_inbox", inbox_id="i123",
        PARSEUR_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_inbox"
    assert "inbox_id" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.get.side_effect = requests.RequestException(response=mock_response)
    
    result = parseur.main(
        operation="list_inboxes",
        PARSEUR_API_KEY="test_key",
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
    
    result = parseur.main(
        operation="list_inboxes",
        PARSEUR_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
