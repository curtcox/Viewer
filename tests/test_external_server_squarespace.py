"""Tests for the Squarespace server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import squarespace


def test_missing_api_key_returns_auth_error():
    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = squarespace.main(
        operation="invalid_op",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_products_dry_run():
    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "list_products"
    assert "api.squarespace.com/1.0/commerce/products" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_product_requires_product_id():
    result = squarespace.main(
        operation="get_product",
        product_id="",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_product_dry_run():
    result = squarespace.main(
        operation="get_product",
        product_id="prod123",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "get_product"
    assert "api.squarespace.com/1.0/commerce/products/prod123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_create_product_requires_name_and_price():
    result = squarespace.main(
        operation="create_product",
        name="",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]

    result = squarespace.main(
        operation="create_product",
        name="Test Product",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_product_dry_run():
    result = squarespace.main(
        operation="create_product",
        name="Test Product",
        price=99.99,
        description="A test product",
        sku="TEST-001",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "create_product"
    assert "api.squarespace.com/1.0/commerce/products" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"
    assert result["output"]["preview"]["payload"]["name"] == "Test Product"
    assert result["output"]["preview"]["payload"]["description"] == "A test product"


def test_update_product_dry_run():
    result = squarespace.main(
        operation="update_product",
        product_id="prod123",
        name="Updated Product",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "update_product"
    assert "api.squarespace.com/1.0/commerce/products/prod123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "PUT"


def test_delete_product_dry_run():
    result = squarespace.main(
        operation="delete_product",
        product_id="prod123",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "delete_product"
    assert "api.squarespace.com/1.0/commerce/products/prod123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "DELETE"


def test_list_orders_dry_run():
    result = squarespace.main(
        operation="list_orders",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "list_orders"
    assert "api.squarespace.com/1.0/commerce/orders" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_order_requires_order_id():
    result = squarespace.main(
        operation="get_order",
        order_id="",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_order_dry_run():
    result = squarespace.main(
        operation="get_order",
        order_id="order123",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "get_order"
    assert "api.squarespace.com/1.0/commerce/orders/order123" in result["output"]["preview"]["url"]


def test_list_inventory_dry_run():
    result = squarespace.main(
        operation="list_inventory",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "list_inventory"
    assert "api.squarespace.com/1.0/commerce/inventory" in result["output"]["preview"]["url"]


def test_update_inventory_requires_quantity():
    result = squarespace.main(
        operation="update_inventory",
        inventory_item_id="inv123",
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_inventory_dry_run():
    result = squarespace.main(
        operation="update_inventory",
        inventory_item_id="inv123",
        quantity=50,
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "update_inventory"
    assert "api.squarespace.com/1.0/commerce/inventory/inv123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "PUT"
    assert result["output"]["preview"]["payload"]["quantity"] == 50


def test_list_products_pagination():
    result = squarespace.main(
        operation="list_products",
        cursor="abc123",
        limit=50,
        SQUARESPACE_API_KEY="test_key",
        dry_run=True,
    )
    assert "preview" in result["output"]
    assert result["output"]["preview"]["params"]["cursor"] == "abc123"
    assert result["output"]["preview"]["params"]["limit"] == 50


def test_list_products_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "products": [{"id": "prod123", "name": "Test Product"}],
        "pagination": {"hasNextPage": False}
    }
    mock_client.request.return_value = mock_response

    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"]["products"][0]["name"] == "Test Product"
    mock_client.request.assert_called_once()


def test_api_401_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.ok = False
    mock_response.json.return_value = {"message": "Unauthorized"}
    mock_client.request.return_value = mock_response

    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="invalid_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_api_404_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Product not found"
    mock_response.ok = False
    mock_response.json.return_value = {"message": "Product not found"}
    mock_client.request.return_value = mock_response

    result = squarespace.main(
        operation="get_product",
        product_id="nonexistent",
        SQUARESPACE_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="test_key",
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

    result = squarespace.main(
        operation="list_products",
        SQUARESPACE_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
