from __future__ import annotations

import requests

from reference.templates.servers.definitions import box


class DummyResponse:
    def __init__(self, status_code: int, json_data, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FakeClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

    def put(self, url: str, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

    def delete(self, url: str, **kwargs):
        self.calls.append(("DELETE", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_access_token():
    result = box.main()

    assert result["output"]["error"] == "Missing BOX_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = box.main(
        operation="unknown",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_file_requires_id():
    result = box.main(
        operation="get_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required file_id"


def test_download_file_requires_id():
    result = box.main(
        operation="download_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required file_id"


def test_upload_file_requires_name():
    result = box.main(
        operation="upload_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required name"


def test_upload_file_requires_content():
    result = box.main(
        operation="upload_file",
        name="test.txt",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required content"


def test_delete_file_requires_id():
    result = box.main(
        operation="delete_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required file_id"


def test_delete_folder_uses_default_when_no_id():
    # When folder_id is not provided, defaults to "0" and shows preview
    result = box.main(
        operation="delete_folder",
        BOX_ACCESS_TOKEN="token",
    )

    # Should show preview, not error, since it defaults to folder "0"
    assert "preview" in result["output"]
    assert result["output"]["preview"]["operation"] == "delete_folder"


def test_create_folder_requires_name():
    result = box.main(
        operation="create_folder",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required name"


def test_copy_file_requires_file_id():
    result = box.main(
        operation="copy_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required file_id"


def test_copy_file_uses_default_parent():
    # When parent_id is not provided, defaults to "0" and shows preview
    result = box.main(
        operation="copy_file",
        file_id="123",
        BOX_ACCESS_TOKEN="token",
    )

    # Should show preview with default parent "0"
    assert "preview" in result["output"]
    assert result["output"]["preview"]["payload"]["parent"]["id"] == "0"


def test_move_file_requires_file_id():
    result = box.main(
        operation="move_file",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required file_id"


def test_move_file_uses_default_parent():
    # When parent_id is not provided, defaults to "0" and shows preview
    result = box.main(
        operation="move_file",
        file_id="123",
        BOX_ACCESS_TOKEN="token",
    )

    # Should show preview with default parent "0"
    assert "preview" in result["output"]
    assert result["output"]["preview"]["payload"]["parent"]["id"] == "0"


def test_search_requires_query():
    result = box.main(
        operation="search",
        BOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required query"


def test_dry_run_preview_for_list_items():
    result = box.main(
        folder_id="123",
        BOX_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_items"
    assert "123" in preview["url"]


def test_dry_run_preview_for_create_folder():
    result = box.main(
        operation="create_folder",
        name="New Folder",
        parent_id="0",
        BOX_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_folder"
    assert preview["payload"]["name"] == "New Folder"
    assert preview["payload"]["parent"]["id"] == "0"


def test_successful_list_items():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"entries": [{"type": "file", "id": "123", "name": "file1.txt"}]},
        )
    )

    result = box.main(
        folder_id="0",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["entries"][0]["name"] == "file1.txt"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_successful_get_file():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"type": "file", "id": "123", "name": "test.txt", "size": 1024},
        )
    )

    result = box.main(
        operation="get_file",
        file_id="123",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["name"] == "test.txt"
    assert result["output"]["size"] == 1024


def test_successful_create_folder():
    fake_client = FakeClient(
        response=DummyResponse(
            201,
            {"type": "folder", "id": "456", "name": "New Folder"},
        )
    )

    result = box.main(
        operation="create_folder",
        name="New Folder",
        parent_id="0",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["name"] == "New Folder"
    assert fake_client.calls[0][0] == "POST"


def test_successful_delete_file():
    fake_client = FakeClient(
        response=DummyResponse(204, {})
    )

    result = box.main(
        operation="delete_file",
        file_id="123",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["message"] == "Successfully deleted"


def test_successful_copy_file():
    fake_client = FakeClient(
        response=DummyResponse(
            201,
            {"type": "file", "id": "789", "name": "copy.txt"},
        )
    )

    result = box.main(
        operation="copy_file",
        file_id="123",
        parent_id="456",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "789"
    assert fake_client.calls[0][0] == "POST"


def test_successful_move_file():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"type": "file", "id": "123", "parent": {"id": "456"}},
        )
    )

    result = box.main(
        operation="move_file",
        file_id="123",
        parent_id="456",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "123"
    assert fake_client.calls[0][0] == "PUT"


def test_download_file_returns_binary():
    fake_client = FakeClient(
        response=DummyResponse(200, {})
    )

    result = box.main(
        operation="download_file",
        file_id="123",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "file" in result["output"]
    assert result["output"]["content_type"] == "application/octet-stream"


def test_successful_search():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"entries": [{"type": "file", "name": "important.txt"}]},
        )
    )

    result = box.main(
        operation="search",
        query="important",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "entries" in result["output"]


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            404,
            {"message": "Item not found", "code": "not_found"},
        )
    )

    result = box.main(
        operation="get_file",
        file_id="999",
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 404


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Connection failed"))

    result = box.main(
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Connection failed" in result["output"]["details"]


def test_invalid_json_response():
    fake_client = FakeClient(
        response=DummyResponse(200, ValueError("Invalid JSON"), text="Not JSON")
    )

    result = box.main(
        BOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
