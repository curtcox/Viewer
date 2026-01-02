"""Tests for the Docparser server definition."""

from unittest.mock import Mock
import requests
from reference_templates.servers.definitions import docparser


def test_missing_api_key_returns_auth_error():
    result = docparser.main(DOCPARSER_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = docparser.main(
        operation="invalid_op",
        DOCPARSER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_upload_document_validation():
    result = docparser.main(
        operation="upload_document", parser_id="p123",
        DOCPARSER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "file_url is required" in str(result["output"]).lower()

def test_get_document_validation():
    result = docparser.main(
        operation="get_document",
        DOCPARSER_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "document_id is required" in str(result["output"]).lower()




def test_dry_run_preview_for_list_parsers():
    result = docparser.main(
        operation="list_parsers",
        DOCPARSER_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "list_parsers"

def test_dry_run_preview_for_get_document():
    result = docparser.main(
        operation="get_document", parser_id="p123", document_id="d123",
        DOCPARSER_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_document"
    assert "document_id" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.get.side_effect = requests.RequestException(response=mock_response)
    
    result = docparser.main(
        operation="list_parsers",
        DOCPARSER_API_KEY="test_key",
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
    
    result = docparser.main(
        operation="list_parsers",
        DOCPARSER_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
