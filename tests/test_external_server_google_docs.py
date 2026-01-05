"""Tests for the Google Docs server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import google_docs


def test_missing_credentials_returns_auth_error():
    result = google_docs.main(GOOGLE_SERVICE_ACCOUNT_JSON=None, GOOGLE_ACCESS_TOKEN=None, dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_docs.main(operation="invalid", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_get_document_requires_document_id():
    result = google_docs.main(operation="get_document", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_create_document_requires_title():
    result = google_docs.main(operation="create_document", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_batch_update_requires_document_id():
    result = google_docs.main(operation="batch_update", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_batch_update_requires_requests_payload():
    result = google_docs.main(operation="batch_update", document_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview():
    result = google_docs.main(operation="create_document", title="Test Doc", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "operation" in result["output"]
    assert "docs.googleapis.com" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = google_docs.main(operation="get_document", document_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"documentId": "123", "title": "Test"}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = google_docs.main(operation="get_document", document_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "documentId" in result["output"]
