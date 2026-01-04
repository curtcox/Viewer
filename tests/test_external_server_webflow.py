"""Tests for the Webflow server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import webflow


def test_missing_api_token_returns_auth_error():
    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = webflow.main(
        operation="invalid_op",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_sites_dry_run():
    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "list_sites"
    assert "api.webflow.com/sites" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_site_requires_site_id():
    result = webflow.main(
        operation="get_site",
        site_id="",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_site_dry_run():
    result = webflow.main(
        operation="get_site",
        site_id="site123",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "get_site"
    assert "api.webflow.com/sites/site123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_list_collections_requires_site_id():
    result = webflow.main(
        operation="list_collections",
        site_id="",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_items_requires_collection_id():
    result = webflow.main(
        operation="list_items",
        collection_id="",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_item_requires_fields():
    result = webflow.main(
        operation="create_item",
        collection_id="coll123",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_item_dry_run():
    result = webflow.main(
        operation="create_item",
        collection_id="coll123",
        fields={"name": "Test Item", "slug": "test-item"},
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "create_item"
    assert "api.webflow.com/collections/coll123/items" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"
    assert result["output"]["preview"]["payload"]["fields"]["name"] == "Test Item"


def test_update_item_requires_item_id():
    result = webflow.main(
        operation="update_item",
        collection_id="coll123",
        item_id="",
        fields={"name": "Updated"},
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_item_dry_run():
    result = webflow.main(
        operation="update_item",
        collection_id="coll123",
        item_id="item456",
        fields={"name": "Updated Item"},
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "update_item"
    assert "api.webflow.com/collections/coll123/items/item456" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "PUT"


def test_delete_item_dry_run():
    result = webflow.main(
        operation="delete_item",
        collection_id="coll123",
        item_id="item456",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "delete_item"
    assert "api.webflow.com/collections/coll123/items/item456" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "DELETE"


def test_publish_site_dry_run():
    result = webflow.main(
        operation="publish_site",
        site_id="site123",
        live=True,
        WEBFLOW_API_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "publish_site"
    assert "api.webflow.com/sites/site123/publish" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"


def test_list_sites_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"_id": "site123", "name": "Test Site"}]
    mock_client.request.return_value = mock_response

    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"][0]["name"] == "Test Site"
    mock_client.request.assert_called_once()


def test_api_401_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_client.request.return_value = mock_response

    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="invalid_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_api_404_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Site not found"
    mock_client.request.return_value = mock_response

    result = webflow.main(
        operation="get_site",
        site_id="nonexistent",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_json_decode_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"Some content"
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid", "", 0)
    mock_response.text = "Invalid JSON"
    mock_client.request.return_value = mock_response

    result = webflow.main(
        operation="list_sites",
        WEBFLOW_API_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
