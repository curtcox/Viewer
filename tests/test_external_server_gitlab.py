"""Tests for the GitLab server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import gitlab


def test_missing_access_token_returns_auth_error():
    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = gitlab.main(
        operation="invalid_op",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_projects_dry_run():
    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_projects"
    assert "gitlab.com/api/v4/projects" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_project_requires_project_id():
    result = gitlab.main(
        operation="get_project",
        project_id="",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_project_dry_run():
    result = gitlab.main(
        operation="get_project",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_project"
    assert "gitlab.com/api/v4/projects/123" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_list_issues_requires_project_id():
    result = gitlab.main(
        operation="list_issues",
        project_id="",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_issues_dry_run():
    result = gitlab.main(
        operation="list_issues",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_issues"
    assert "gitlab.com/api/v4/projects/123/issues" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_issue_requires_issue_iid():
    result = gitlab.main(
        operation="get_issue",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_issue_dry_run():
    result = gitlab.main(
        operation="get_issue",
        project_id="123",
        issue_iid=456,
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_issue"
    assert "gitlab.com/api/v4/projects/123/issues/456" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_create_issue_requires_title():
    result = gitlab.main(
        operation="create_issue",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_issue_dry_run():
    result = gitlab.main(
        operation="create_issue",
        project_id="123",
        title="Test Issue",
        description="Test description",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "create_issue"
    assert "gitlab.com/api/v4/projects/123/issues" in result["output"]["url"]
    assert result["output"]["method"] == "POST"
    assert result["output"]["payload"]["title"] == "Test Issue"
    assert result["output"]["payload"]["description"] == "Test description"


def test_list_merge_requests_dry_run():
    result = gitlab.main(
        operation="list_merge_requests",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_merge_requests"
    assert "gitlab.com/api/v4/projects/123/merge_requests" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_merge_request_requires_mr_iid():
    result = gitlab.main(
        operation="get_merge_request",
        project_id="123",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_merge_request_dry_run():
    result = gitlab.main(
        operation="get_merge_request",
        project_id="123",
        mr_iid=789,
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_merge_request"
    assert "gitlab.com/api/v4/projects/123/merge_requests/789" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_custom_gitlab_url():
    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="test_token",
        GITLAB_URL="https://gitlab.example.com",
        dry_run=True,
    )
    assert "gitlab.example.com/api/v4/projects" in result["output"]["url"]


def test_list_projects_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": 1, "name": "test"}]
    mock_client.request.return_value = mock_response

    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"] == [{"id": 1, "name": "test"}]
    mock_client.request.assert_called_once()


def test_api_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_client.request.return_value = mock_response

    result = gitlab.main(
        operation="get_project",
        project_id="999",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="test_token",
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

    result = gitlab.main(
        operation="list_projects",
        GITLAB_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON" in result["output"]["error"]
