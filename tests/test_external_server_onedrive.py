"""Tests for the OneDrive server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import onedrive


def test_missing_credentials_returns_auth_error():
    result = onedrive.main(
        MICROSOFT_ACCESS_TOKEN=None,
        MICROSOFT_TENANT_ID=None,
        MICROSOFT_CLIENT_ID=None,
        MICROSOFT_CLIENT_SECRET=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = onedrive.main(
        operation="invalid_op",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_item_requires_item_id_or_path():
    result = onedrive.main(
        operation="get_item",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_upload_file_requires_file_name_and_content():
    result = onedrive.main(
        operation="upload_file",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_folder_requires_folder_name():
    result = onedrive.main(
        operation="create_folder",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_items():
    result = onedrive.main(
        operation="list_items",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "graph.microsoft.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_upload_file():
    result = onedrive.main(
        operation="upload_file",
        file_name="test.txt",
        file_content="Hello World",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "PUT"


def test_list_items_with_path():
    result = onedrive.main(
        operation="list_items",
        path="/Documents",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "Documents" in result["output"]["url"]


def test_list_items_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [{"id": "item1", "name": "doc.txt"}]}
    mock_client.get.return_value = mock_response

    result = onedrive.main(
        operation="list_items",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "value" in result["output"]


def test_get_item_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "item1", "name": "doc.txt"}
    mock_client.get.return_value = mock_response

    result = onedrive.main(
        operation="get_item",
        item_id="item1",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["id"] == "item1"


def test_delete_item_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 204
    mock_client.delete.return_value = mock_response

    result = onedrive.main(
        operation="delete_item",
        item_id="item1",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_create_folder_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "folder1", "name": "NewFolder"}
    mock_client.post.return_value = mock_response

    result = onedrive.main(
        operation="create_folder",
        folder_name="NewFolder",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["name"] == "NewFolder"


def test_api_error_handling():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Item not found"}}
    mock_client.get.return_value = mock_response

    result = onedrive.main(
        operation="get_item",
        item_id="nonexistent",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_request_exception_handling():
    mock_client = Mock()
    mock_client.get.side_effect = requests.RequestException("Network error")

    result = onedrive.main(
        operation="list_items",
        MICROSOFT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]
