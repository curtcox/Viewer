from __future__ import annotations

from reference_templates.servers.definitions import azure_blob


class DummyResponse:
    def __init__(self, status_code: int, text: str = "", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.ok = status_code < 400


class FakeClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, dict]] = []

    def request(self, **kwargs):
        self.calls.append((kwargs.get("method"), kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_account_name():
    result = azure_blob.main()

    assert "Missing AZURE_STORAGE_ACCOUNT or AZURE_STORAGE_CONNECTION_STRING" in result["output"]["error"]
    assert result["output"]["status_code"] == 401


def test_requires_account_key():
    result = azure_blob.main(AZURE_STORAGE_ACCOUNT="myaccount")

    assert "Missing AZURE_STORAGE_KEY or AZURE_STORAGE_CONNECTION_STRING" in result["output"]["error"]
    assert result["output"]["status_code"] == 401


def test_accepts_connection_string():
    result = azure_blob.main(
        operation="list_containers",
        AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_containers"


def test_invalid_operation_returns_validation_error():
    result = azure_blob.main(
        operation="unknown",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_list_blobs_requires_container():
    result = azure_blob.main(
        operation="list_blobs",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
    )

    assert result["output"]["error"]["message"] == "Missing required container"


def test_get_blob_requires_blob_name():
    result = azure_blob.main(
        operation="get_blob",
        container="mycontainer",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
    )

    assert result["output"]["error"]["message"] == "Missing required blob_name"


def test_upload_blob_requires_content():
    result = azure_blob.main(
        operation="upload_blob",
        container="mycontainer",
        blob_name="test.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
    )

    assert result["output"]["error"]["message"] == "Missing required content"


def test_copy_blob_requires_to_blob():
    result = azure_blob.main(
        operation="copy_blob",
        container="mycontainer",
        blob_name="source.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
    )

    assert result["output"]["error"]["message"] == "Missing required to_blob"


def test_dry_run_list_containers():
    result = azure_blob.main(
        operation="list_containers",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_containers"
    assert result["output"]["method"] == "GET"
    assert "myaccount.blob.core.windows.net" in result["output"]["url"]


def test_dry_run_list_blobs():
    result = azure_blob.main(
        operation="list_blobs",
        container="mycontainer",
        prefix="uploads/",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_blobs"
    assert result["output"]["method"] == "GET"
    assert "mycontainer" in result["output"]["url"]
    assert result["output"]["params"]["prefix"] == "uploads/"


def test_dry_run_get_blob():
    result = azure_blob.main(
        operation="get_blob",
        container="mycontainer",
        blob_name="file.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_blob"
    assert result["output"]["method"] == "GET"
    assert "mycontainer/file.txt" in result["output"]["url"]


def test_dry_run_upload_blob():
    result = azure_blob.main(
        operation="upload_blob",
        container="mycontainer",
        blob_name="file.txt",
        content="Hello, World!",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "upload_blob"
    assert result["output"]["method"] == "PUT"


def test_dry_run_delete_blob():
    result = azure_blob.main(
        operation="delete_blob",
        container="mycontainer",
        blob_name="file.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "delete_blob"
    assert result["output"]["method"] == "DELETE"


def test_dry_run_create_container():
    result = azure_blob.main(
        operation="create_container",
        container="newcontainer",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "create_container"
    assert result["output"]["method"] == "PUT"


def test_dry_run_get_container_properties():
    result = azure_blob.main(
        operation="get_container_properties",
        container="mycontainer",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_container_properties"
    assert result["output"]["method"] == "GET"


def test_dry_run_copy_blob():
    result = azure_blob.main(
        operation="copy_blob",
        container="mycontainer",
        blob_name="source.txt",
        to_blob="dest.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "copy_blob"
    assert result["output"]["method"] == "PUT"


def test_dry_run_get_blob_properties():
    result = azure_blob.main(
        operation="get_blob_properties",
        container="mycontainer",
        blob_name="file.txt",
        AZURE_STORAGE_ACCOUNT="myaccount",
        AZURE_STORAGE_KEY="mykey",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_blob_properties"
    assert result["output"]["method"] == "HEAD"
