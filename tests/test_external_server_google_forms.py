"""Tests for the Google Forms server definition."""

from unittest.mock import Mock
import requests
from reference.templates.servers.definitions import google_forms


def test_missing_credentials_returns_auth_error():
    result = google_forms.main(GOOGLE_SERVICE_ACCOUNT_JSON=None, GOOGLE_ACCESS_TOKEN=None, dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = google_forms.main(operation="invalid", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_get_form_requires_form_id():
    result = google_forms.main(operation="get_form", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_create_form_requires_title():
    result = google_forms.main(operation="create_form", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_list_responses_requires_form_id():
    result = google_forms.main(operation="list_responses", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "error" in result["output"]


def test_dry_run_returns_preview():
    result = google_forms.main(operation="create_form", title="Test Form", GOOGLE_ACCESS_TOKEN="test", dry_run=True)
    assert "operation" in result["output"]
    assert "forms.googleapis.com" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")
    result = google_forms.main(operation="get_form", form_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"formId": "123", "info": {"title": "Test"}}
    mock_client = Mock()
    mock_client.request.return_value = mock_response
    result = google_forms.main(operation="get_form", form_id="123", GOOGLE_ACCESS_TOKEN="test", dry_run=False, client=mock_client)
    assert "formId" in result["output"]
