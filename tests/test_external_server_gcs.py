from __future__ import annotations

from reference.templates.servers.definitions import gcs


class DummyResponse:
    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or (str(json_data) if json_data else "")
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data or {}


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


def test_requires_credentials():
    result = gcs.main()

    assert "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN" in result["output"]["error"]
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = gcs.main(
        operation="unknown",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_list_buckets_requires_project_id():
    result = gcs.main(
        operation="list_buckets",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required project_id for list_buckets"


def test_list_objects_requires_bucket():
    result = gcs.main(
        operation="list_objects",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required bucket"


def test_get_object_requires_object_name():
    result = gcs.main(
        operation="get_object",
        bucket="my-bucket",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required object_name"


def test_upload_object_requires_content():
    result = gcs.main(
        operation="upload_object",
        bucket="my-bucket",
        object_name="test.txt",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required content"


def test_copy_object_requires_to_object():
    result = gcs.main(
        operation="copy_object",
        bucket="my-bucket",
        object_name="source.txt",
        GOOGLE_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Missing required to_object"


def test_dry_run_list_buckets():
    result = gcs.main(
        operation="list_buckets",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_buckets"
    assert result["output"]["method"] == "GET"
    assert "storage.googleapis.com/storage/v1/b" in result["output"]["url"]


def test_dry_run_list_objects():
    result = gcs.main(
        operation="list_objects",
        bucket="my-bucket",
        prefix="uploads/",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_objects"
    assert result["output"]["method"] == "GET"
    assert "my-bucket/o" in result["output"]["url"]
    assert result["output"]["params"]["prefix"] == "uploads/"


def test_dry_run_get_object():
    result = gcs.main(
        operation="get_object",
        bucket="my-bucket",
        object_name="file.txt",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_object"
    assert result["output"]["method"] == "GET"
    assert "my-bucket/o/file.txt" in result["output"]["url"]


def test_dry_run_upload_object():
    result = gcs.main(
        operation="upload_object",
        bucket="my-bucket",
        object_name="file.txt",
        content="Hello, World!",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "upload_object"
    assert result["output"]["method"] == "POST"


def test_dry_run_delete_object():
    result = gcs.main(
        operation="delete_object",
        bucket="my-bucket",
        object_name="file.txt",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "delete_object"
    assert result["output"]["method"] == "DELETE"


def test_dry_run_create_bucket():
    result = gcs.main(
        operation="create_bucket",
        bucket="new-bucket",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "create_bucket"
    assert result["output"]["method"] == "POST"


def test_dry_run_get_bucket():
    result = gcs.main(
        operation="get_bucket",
        bucket="my-bucket",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_bucket"
    assert result["output"]["method"] == "GET"


def test_dry_run_copy_object():
    result = gcs.main(
        operation="copy_object",
        bucket="my-bucket",
        object_name="source.txt",
        to_object="dest.txt",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "copy_object"
    assert result["output"]["method"] == "POST"


def test_accepts_service_account_json():
    result = gcs.main(
        operation="list_buckets",
        project_id="my-project",
        GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account"}',
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_buckets"


def test_accepts_access_token():
    result = gcs.main(
        operation="list_buckets",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_buckets"
