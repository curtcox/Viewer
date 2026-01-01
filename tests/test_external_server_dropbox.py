from __future__ import annotations

import requests

from reference_templates.servers.definitions import dropbox


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

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_access_token():
    result = dropbox.main()

    assert result["output"]["error"] == "Missing DROPBOX_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = dropbox.main(
        operation="unknown",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_metadata_requires_path():
    result = dropbox.main(
        operation="get_metadata",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path"


def test_download_requires_path():
    result = dropbox.main(
        operation="download",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path"


def test_upload_requires_path():
    result = dropbox.main(
        operation="upload",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path"


def test_upload_requires_content():
    result = dropbox.main(
        operation="upload",
        path="/test.txt",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required content"


def test_delete_requires_path():
    result = dropbox.main(
        operation="delete",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path"


def test_create_folder_requires_path():
    result = dropbox.main(
        operation="create_folder",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path"


def test_move_requires_path():
    result = dropbox.main(
        operation="move",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path (from_path)"


def test_move_requires_to_path():
    result = dropbox.main(
        operation="move",
        path="/source.txt",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required to_path"


def test_copy_requires_path():
    result = dropbox.main(
        operation="copy",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required path (from_path)"


def test_copy_requires_to_path():
    result = dropbox.main(
        operation="copy",
        path="/source.txt",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required to_path"


def test_search_requires_query():
    result = dropbox.main(
        operation="search",
        DROPBOX_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required query"


def test_dry_run_preview_for_list_folder():
    result = dropbox.main(
        path="/Documents",
        DROPBOX_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "list_folder"
    assert preview["payload"]["path"] == "/Documents"


def test_dry_run_preview_for_create_folder():
    result = dropbox.main(
        operation="create_folder",
        path="/NewFolder",
        DROPBOX_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_folder"
    assert preview["payload"]["path"] == "/NewFolder"


def test_successful_list_folder():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"entries": [{"name": "file1.txt", ".tag": "file"}], "has_more": False},
        )
    )

    result = dropbox.main(
        path="/Documents",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["entries"][0]["name"] == "file1.txt"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "POST"


def test_successful_get_metadata():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"name": "file.txt", ".tag": "file", "size": 1024},
        )
    )

    result = dropbox.main(
        operation="get_metadata",
        path="/file.txt",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["name"] == "file.txt"
    assert result["output"]["size"] == 1024


def test_successful_create_folder():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"name": "NewFolder", ".tag": "folder"},
        )
    )

    result = dropbox.main(
        operation="create_folder",
        path="/NewFolder",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["name"] == "NewFolder"


def test_download_returns_binary():
    fake_client = FakeClient(
        response=DummyResponse(200, {})
    )

    result = dropbox.main(
        operation="download",
        path="/file.txt",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "file" in result["output"]
    assert result["output"]["content_type"] == "application/octet-stream"


def test_successful_search():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"matches": [{"metadata": {"name": "result.txt"}}]},
        )
    )

    result = dropbox.main(
        operation="search",
        query="important",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "matches" in result["output"]


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400,
            {"error_summary": "path/not_found/", "error": {".tag": "path"}},
        )
    )

    result = dropbox.main(
        path="/missing",
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Connection failed"))

    result = dropbox.main(
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Connection failed" in result["output"]["details"]


def test_invalid_json_response():
    fake_client = FakeClient(
        response=DummyResponse(200, ValueError("Invalid JSON"), text="Not JSON")
    )

    result = dropbox.main(
        DROPBOX_ACCESS_TOKEN="token",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
