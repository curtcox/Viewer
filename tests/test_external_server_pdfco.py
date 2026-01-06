"""Tests for the PDF.co server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import pdfco


def test_missing_api_key_returns_auth_error():
    result = pdfco.main(PDFCO_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = pdfco.main(
        operation="invalid_op",
        PDFCO_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]



def test_pdf_to_text_validation():
    result = pdfco.main(
        operation="pdf_to_text",
        PDFCO_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "url is required" in str(result["output"]).lower()




def test_dry_run_preview_for_pdf_to_text():
    result = pdfco.main(
        operation="pdf_to_text", url="https://example.com/doc.pdf",
        PDFCO_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "pdf_to_text"
    assert "pdf_url" in result["output"]

def test_dry_run_preview_for_pdf_info():
    result = pdfco.main(
        operation="pdf_info", url="https://example.com/doc.pdf",
        PDFCO_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "pdf_info"
    assert "pdf_url" in result["output"]



def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.post.side_effect = requests.RequestException(response=mock_response)

    result = pdfco.main(
        operation="pdf_to_text", url="https://example.com/doc.pdf",
        PDFCO_API_KEY="test_key",
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

    result = pdfco.main(
        operation="pdf_to_text", url="https://example.com/doc.pdf",
        PDFCO_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["result"] == "success"
