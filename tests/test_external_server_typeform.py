"""Tests for the Typeform server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import typeform


def test_missing_api_token_returns_auth_error():
    result = typeform.main(TYPEFORM_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = typeform.main(
        operation="invalid_op", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_form_requires_form_id():
    result = typeform.main(
        operation="get_form", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_create_form_requires_title():
    result = typeform.main(
        operation="create_form", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_list_responses_requires_form_id():
    result = typeform.main(
        operation="list_responses", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_get_response_requires_both_ids():
    result = typeform.main(
        operation="get_response", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_delete_form_requires_form_id():
    result = typeform.main(
        operation="delete_form", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_forms():
    result = typeform.main(
        operation="list_forms", TYPEFORM_ACCESS_TOKEN="test_token", dry_run=True
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "forms" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_form():
    result = typeform.main(
        operation="create_form",
        title="Test Form",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_form():
    result = typeform.main(
        operation="get_form",
        form_id="abc123",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "abc123" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_responses():
    result = typeform.main(
        operation="list_responses",
        form_id="abc123",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "responses" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_workspaces():
    result = typeform.main(
        operation="list_workspaces",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "workspaces" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = typeform.main(
        operation="list_forms",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_json_parsing_error_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Not JSON"
    mock_client.request.return_value = mock_response

    result = typeform.main(
        operation="list_forms",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"items": [{"id": "form1", "title": "Test"}]}
    mock_client.request.return_value = mock_response

    result = typeform.main(
        operation="list_forms",
        TYPEFORM_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )
    assert "items" in result["output"]
