"""Tests for the YouTube server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import youtube


def test_missing_credentials_returns_auth_error():
    result = youtube.main(
        GOOGLE_SERVICE_ACCOUNT_JSON=None,
        GOOGLE_ACCESS_TOKEN=None,
        YOUTUBE_API_KEY=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = youtube.main(
        operation="invalid_op",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_videos_requires_video_id():
    result = youtube.main(
        operation="list_videos",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_video_requires_video_id():
    result = youtube.main(
        operation="get_video",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_search_videos_requires_query():
    result = youtube.main(
        operation="search_videos",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_channels_requires_channel_id():
    result = youtube.main(
        operation="list_channels",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_comments_requires_video_id():
    result = youtube.main(
        operation="list_comments",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_search_videos():
    result = youtube.main(
        operation="search_videos",
        query="python tutorial",
        YOUTUBE_API_KEY="test-key",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "www.googleapis.com/youtube" in result["output"]["url"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = youtube.main(
        operation="search_videos",
        query="test",
        YOUTUBE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 200
    mock_response.text = "Not JSON"

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = youtube.main(
        operation="search_videos",
        query="test",
        YOUTUBE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": {"message": "Invalid request", "code": 400}
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = youtube.main(
        operation="search_videos",
        query="test",
        YOUTUBE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "items": [{"id": {"videoId": "123"}, "snippet": {"title": "Test Video"}}],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = youtube.main(
        operation="search_videos",
        query="test",
        YOUTUBE_API_KEY="test-key",
        dry_run=False,
        client=mock_client,
    )
    assert "items" in result["output"]
