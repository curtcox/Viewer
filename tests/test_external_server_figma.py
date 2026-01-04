"""Tests for the Figma server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import figma


def test_missing_access_token_returns_auth_error():
    result = figma.main(
        operation="list_files",
        FIGMA_ACCESS_TOKEN="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = figma.main(
        operation="invalid_op",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_files_dry_run():
    result = figma.main(
        operation="list_files",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_files"
    assert "api.figma.com/v1/me/files" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_file_requires_file_key():
    result = figma.main(
        operation="get_file",
        file_key="",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_file_dry_run():
    result = figma.main(
        operation="get_file",
        file_key="abc123",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_file"
    assert "api.figma.com/v1/files/abc123" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_list_comments_requires_file_key():
    result = figma.main(
        operation="list_comments",
        file_key="",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_comments_dry_run():
    result = figma.main(
        operation="list_comments",
        file_key="abc123",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_comments"
    assert "api.figma.com/v1/files/abc123/comments" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_comment_requires_comment_id():
    result = figma.main(
        operation="get_comment",
        file_key="abc123",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_comment_dry_run():
    result = figma.main(
        operation="get_comment",
        file_key="abc123",
        comment_id="comment456",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_comment"
    assert "api.figma.com/v1/files/abc123/comments/comment456" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_create_comment_requires_message():
    result = figma.main(
        operation="create_comment",
        file_key="abc123",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_comment_dry_run():
    result = figma.main(
        operation="create_comment",
        file_key="abc123",
        message="Great design!",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "create_comment"
    assert "api.figma.com/v1/files/abc123/comments" in result["output"]["url"]
    assert result["output"]["method"] == "POST"
    assert result["output"]["payload"]["message"] == "Great design!"


def test_delete_comment_requires_comment_id():
    result = figma.main(
        operation="delete_comment",
        file_key="abc123",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_comment_dry_run():
    result = figma.main(
        operation="delete_comment",
        file_key="abc123",
        comment_id="comment456",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "delete_comment"
    assert "api.figma.com/v1/files/abc123/comments/comment456" in result["output"]["url"]
    assert result["output"]["method"] == "DELETE"


def test_list_files_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"files": [{"key": "abc123", "name": "Test File"}]}
    mock_client.request.return_value = mock_response

    result = figma.main(
        operation="list_files",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"]["files"][0]["name"] == "Test File"
    mock_client.request.assert_called_once()


def test_delete_comment_success():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 204
    mock_client.request.return_value = mock_response

    result = figma.main(
        operation="delete_comment",
        file_key="abc123",
        comment_id="comment456",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"]["success"] is True
    assert "deleted" in result["output"]["message"]


def test_api_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "File not found"
    mock_client.request.return_value = mock_response

    result = figma.main(
        operation="get_file",
        file_key="nonexistent",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = figma.main(
        operation="list_files",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
    assert "timed out" in result["output"]["error"]


def test_json_decode_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid", "", 0)
    mock_response.text = "Invalid JSON"
    mock_client.request.return_value = mock_response

    result = figma.main(
        operation="list_files",
        FIGMA_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON" in result["output"]["error"]
