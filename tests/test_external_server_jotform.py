"""Tests for the Jotform server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import jotform


def test_missing_api_key_returns_auth_error():
    result = jotform.main(JOTFORM_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = jotform.main(
        operation="invalid_op", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_get_form_requires_form_id():
    result = jotform.main(
        operation="get_form", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_create_form_requires_title():
    result = jotform.main(
        operation="create_form", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_list_submissions_requires_form_id():
    result = jotform.main(
        operation="list_submissions", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_get_submission_requires_submission_id():
    result = jotform.main(
        operation="get_submission", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_list_questions_requires_form_id():
    result = jotform.main(
        operation="list_questions", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_delete_form_requires_form_id():
    result = jotform.main(
        operation="delete_form", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_forms():
    result = jotform.main(
        operation="list_forms", JOTFORM_API_KEY="test_key", dry_run=True
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "forms" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_form():
    result = jotform.main(
        operation="create_form",
        form_title="Test Form",
        JOTFORM_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_get_form():
    result = jotform.main(
        operation="get_form",
        form_id="123456789012345",
        JOTFORM_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "123456789012345" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_submissions():
    result = jotform.main(
        operation="list_submissions",
        form_id="123456789012345",
        JOTFORM_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "submissions" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_questions():
    result = jotform.main(
        operation="list_questions",
        form_id="123456789012345",
        JOTFORM_API_KEY="test_key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "questions" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = jotform.main(
        operation="list_forms",
        JOTFORM_API_KEY="test_key",
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

    result = jotform.main(
        operation="list_forms",
        JOTFORM_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"content": [{"id": "form1", "title": "Test"}]}
    mock_client.request.return_value = mock_response

    result = jotform.main(
        operation="list_forms",
        JOTFORM_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "content" in result["output"]
