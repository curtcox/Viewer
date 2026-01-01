"""Tests for the Miro server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import miro


def test_missing_access_token_returns_auth_error():
    result = miro.main(
        operation="list_boards",
        MIRO_ACCESS_TOKEN="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = miro.main(
        operation="invalid_op",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_boards_dry_run():
    result = miro.main(
        operation="list_boards",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_boards"
    assert "api.miro.com/v2/boards" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_board_requires_board_id():
    result = miro.main(
        operation="get_board",
        board_id="",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_board_dry_run():
    result = miro.main(
        operation="get_board",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_board"
    assert "api.miro.com/v2/boards/board123" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_list_items_requires_board_id():
    result = miro.main(
        operation="list_items",
        board_id="",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_items_dry_run():
    result = miro.main(
        operation="list_items",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_items"
    assert "api.miro.com/v2/boards/board123/items" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_item_requires_item_id():
    result = miro.main(
        operation="get_item",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_item_dry_run():
    result = miro.main(
        operation="get_item",
        board_id="board123",
        item_id="item456",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_item"
    assert "api.miro.com/v2/boards/board123/items/item456" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_create_item_requires_data():
    result = miro.main(
        operation="create_item",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_item_dry_run():
    result = miro.main(
        operation="create_item",
        board_id="board123",
        data={"title": "Test Card"},
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "create_item"
    assert "api.miro.com/v2/boards/board123/items" in result["output"]["url"]
    assert result["output"]["method"] == "POST"
    assert result["output"]["payload"]["type"] == "card"
    assert result["output"]["payload"]["data"] == {"title": "Test Card"}


def test_list_widgets_dry_run():
    result = miro.main(
        operation="list_widgets",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "list_widgets"
    assert "api.miro.com/v2/boards/board123/widgets" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_get_widget_requires_widget_id():
    result = miro.main(
        operation="get_widget",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_widget_dry_run():
    result = miro.main(
        operation="get_widget",
        board_id="board123",
        widget_id="widget789",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "get_widget"
    assert "api.miro.com/v2/boards/board123/widgets/widget789" in result["output"]["url"]
    assert result["output"]["method"] == "GET"


def test_create_widget_requires_data():
    result = miro.main(
        operation="create_widget",
        board_id="board123",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_widget_dry_run():
    result = miro.main(
        operation="create_widget",
        board_id="board123",
        data={"text": "Test Shape"},
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=True,
    )
    assert result["output"]["operation"] == "create_widget"
    assert "api.miro.com/v2/boards/board123/widgets" in result["output"]["url"]
    assert result["output"]["method"] == "POST"


def test_list_boards_with_mocked_client():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "board1", "name": "Test Board"}]}
    mock_client.request.return_value = mock_response

    result = miro.main(
        operation="list_boards",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert result["output"]["data"][0]["name"] == "Test Board"
    mock_client.request.assert_called_once()


def test_api_error_handling():
    mock_client = Mock(spec=["request"])
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_client.request.return_value = mock_response

    result = miro.main(
        operation="get_board",
        board_id="nonexistent",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]


def test_timeout_handling():
    mock_client = Mock(spec=["request"])
    mock_client.request.side_effect = requests.exceptions.Timeout("Request timed out")

    result = miro.main(
        operation="list_boards",
        MIRO_ACCESS_TOKEN="test_token",
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

    result = miro.main(
        operation="list_boards",
        MIRO_ACCESS_TOKEN="test_token",
        dry_run=False,
        client=mock_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON" in result["output"]["error"]
