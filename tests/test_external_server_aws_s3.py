from __future__ import annotations

import requests

from reference.templates.servers.definitions import aws_s3


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
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


def test_requires_access_key():
    result = aws_s3.main()

    assert result["output"]["error"] == "Missing AWS_ACCESS_KEY_ID"
    assert result["output"]["status_code"] == 401


def test_requires_secret_key():
    result = aws_s3.main(AWS_ACCESS_KEY_ID="key")

    assert result["output"]["error"] == "Missing AWS_SECRET_ACCESS_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = aws_s3.main(
        operation="unknown",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_list_objects_requires_bucket():
    result = aws_s3.main(
        operation="list_objects",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required bucket"


def test_get_object_requires_key():
    result = aws_s3.main(
        operation="get_object",
        bucket="my-bucket",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required key"


def test_put_object_requires_content():
    result = aws_s3.main(
        operation="put_object",
        bucket="my-bucket",
        key="test.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required content"


def test_copy_object_requires_to_key():
    result = aws_s3.main(
        operation="copy_object",
        bucket="my-bucket",
        key="source.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
    )

    assert result["output"]["error"]["message"] == "Missing required to_key"


def test_dry_run_list_buckets():
    result = aws_s3.main(
        operation="list_buckets",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_buckets"
    assert result["output"]["method"] == "GET"
    assert "s3.us-east-1.amazonaws.com" in result["output"]["url"]


def test_dry_run_list_objects():
    result = aws_s3.main(
        operation="list_objects",
        bucket="my-bucket",
        prefix="uploads/",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "list_objects"
    assert result["output"]["method"] == "GET"
    assert "my-bucket.s3.us-east-1.amazonaws.com" in result["output"]["url"]
    assert result["output"]["params"]["prefix"] == "uploads/"


def test_dry_run_get_object():
    result = aws_s3.main(
        operation="get_object",
        bucket="my-bucket",
        key="file.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "get_object"
    assert result["output"]["method"] == "GET"
    assert "my-bucket.s3.us-east-1.amazonaws.com" in result["output"]["url"]
    assert "file.txt" in result["output"]["url"]


def test_dry_run_put_object():
    result = aws_s3.main(
        operation="put_object",
        bucket="my-bucket",
        key="file.txt",
        content="Hello, World!",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "put_object"
    assert result["output"]["method"] == "PUT"


def test_dry_run_delete_object():
    result = aws_s3.main(
        operation="delete_object",
        bucket="my-bucket",
        key="file.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "delete_object"
    assert result["output"]["method"] == "DELETE"


def test_dry_run_create_bucket():
    result = aws_s3.main(
        operation="create_bucket",
        bucket="new-bucket",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "create_bucket"
    assert result["output"]["method"] == "PUT"


def test_dry_run_copy_object():
    result = aws_s3.main(
        operation="copy_object",
        bucket="my-bucket",
        key="source.txt",
        to_key="dest.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "copy_object"
    assert result["output"]["method"] == "PUT"


def test_dry_run_head_object():
    result = aws_s3.main(
        operation="head_object",
        bucket="my-bucket",
        key="file.txt",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=True,
    )

    assert "output" in result
    assert result["output"]["operation"] == "head_object"
    assert result["output"]["method"] == "HEAD"


def test_actual_call_success():
    fake_response = DummyResponse(200, text="<ListAllMyBucketsResult/>")
    fake_client = FakeClient(response=fake_response)

    result = aws_s3.main(
        operation="list_buckets",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=False,
        client=fake_client,
    )

    assert "output" in result
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_actual_call_error():
    fake_response = DummyResponse(403, text="<Error><Code>AccessDenied</Code></Error>")
    fake_client = FakeClient(response=fake_response)

    result = aws_s3.main(
        operation="list_buckets",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=False,
        client=fake_client,
    )

    assert "output" in result
    assert "error" in result["output"]
    assert result["output"]["status_code"] == 403


def test_actual_call_exception():
    fake_client = FakeClient(exc=requests.exceptions.Timeout("Timeout"))

    result = aws_s3.main(
        operation="list_buckets",
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        dry_run=False,
        client=fake_client,
    )

    assert "output" in result
    assert "error" in result["output"]
    assert result["output"]["status_code"] == 500
