"""Tests for the Wix server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import wix


def test_missing_api_key_returns_auth_error():
    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = wix.main(
        operation="invalid_op",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_collections_dry_run():
    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "list_collections"
    assert "wixapis.com/wix-data/v2/collections" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_site_requires_site_id():
    result = wix.main(
        operation="get_site",
        site_id="",
        WIX_API_KEY="test_key",
        WIX_SITE_ID="",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_site_dry_run():
    result = wix.main(
        operation="get_site",
        site_id="site123",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "get_site"
    assert "wixapis.com/v2/sites/site123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_site_uses_wix_site_id_fallback():
    result = wix.main(
        operation="get_site",
        WIX_API_KEY="test_key",
        WIX_SITE_ID="fallback_site",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert "wixapis.com/v2/sites/fallback_site" in result["output"]["preview"]["url"]


def test_query_items_requires_data_collection_id():
    result = wix.main(
        operation="query_items",
        data_collection_id="",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_query_items_dry_run():
    result = wix.main(
        operation="query_items",
        data_collection_id="products",
        paging_limit=10,
        paging_offset=0,
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "query_items"
    assert "wixapis.com/wix-data/v2/items/query" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"
    assert result["output"]["preview"]["payload"]["dataCollectionId"] == "products"
    assert result["output"]["preview"]["payload"]["query"]["paging"]["limit"] == 10


def test_create_item_requires_fields():
    result = wix.main(
        operation="create_item",
        data_collection_id="products",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_item_dry_run():
    result = wix.main(
        operation="create_item",
        data_collection_id="products",
        fields={"name": "Test Product", "price": 99.99},
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "create_item"
    assert "wixapis.com/wix-data/v2/items" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"
    assert result["output"]["preview"]["payload"]["dataItem"]["data"]["name"] == "Test Product"


def test_update_item_requires_item_id():
    result = wix.main(
        operation="update_item",
        data_collection_id="products",
        item_id="",
        fields={"name": "Updated"},
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_item_dry_run():
    result = wix.main(
        operation="update_item",
        data_collection_id="products",
        item_id="item123",
        fields={"name": "Updated Product"},
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "update_item"
    assert "wixapis.com/wix-data/v2/items/item123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "PATCH"


def test_delete_item_dry_run():
    result = wix.main(
        operation="delete_item",
        data_collection_id="products",
        item_id="item123",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "delete_item"
    assert "wixapis.com/wix-data/v2/items/item123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "DELETE"


def test_get_item_dry_run():
    result = wix.main(
        operation="get_item",
        data_collection_id="products",
        item_id="item123",
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "get_item"
    assert "wixapis.com/wix-data/v2/items/item123" in result["output"]["preview"]["url"]


def test_query_items_with_filter():
    result = wix.main(
        operation="query_items",
        data_collection_id="products",
        filter_json={"price": {"$gt": 50}},
        WIX_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["payload"]["query"]["filter"] == {"price": {"$gt": 50}}


def test_list_collections_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"collections": [{"id": "products", "displayName": "Products"}]}
    mock_client.request.return_value = mock_response

    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"]["collections"][0]["displayName"] == "Products"
    mock_client.request.assert_called_once()


def test_api_401_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_client.request.return_value = mock_response

    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="invalid_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_api_404_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Collection not found"
    mock_client.request.return_value = mock_response

    result = wix.main(
        operation="get_collection",
        collection_id="nonexistent",
        WIX_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="test_key",
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

    result = wix.main(
        operation="list_collections",
        WIX_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
