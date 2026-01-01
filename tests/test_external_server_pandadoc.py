from __future__ import annotations

import requests

from reference_templates.servers.definitions import pandadoc


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


def test_requires_api_key():
    result = pandadoc.main()

    assert result["output"]["error"] == "Missing PANDADOC_API_KEY"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = pandadoc.main(
        operation="unknown",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_document_requires_id():
    result = pandadoc.main(
        operation="get_document",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required document_id"


def test_create_document_requires_name():
    result = pandadoc.main(
        operation="create_document",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required name"


def test_create_document_requires_template_uuid():
    result = pandadoc.main(
        operation="create_document",
        name="Test Doc",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required template_uuid"


def test_create_document_requires_recipient_email():
    result = pandadoc.main(
        operation="create_document",
        name="Test Doc",
        template_uuid="template123",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required recipient_email"


def test_send_document_requires_id():
    result = pandadoc.main(
        operation="send_document",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required document_id"


def test_download_document_requires_id():
    result = pandadoc.main(
        operation="download_document",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required document_id"


def test_get_template_requires_id():
    result = pandadoc.main(
        operation="get_template",
        PANDADOC_API_KEY="api-key",
    )

    assert result["output"]["error"]["message"] == "Missing required template_id"


def test_dry_run_preview_for_list_documents():
    result = pandadoc.main(
        PANDADOC_API_KEY="api-key",
        status="draft",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_documents"
    assert preview["params"]["status"] == "draft"


def test_dry_run_preview_for_create_document():
    result = pandadoc.main(
        operation="create_document",
        name="Test Document",
        template_uuid="template123",
        recipient_email="test@example.com",
        PANDADOC_API_KEY="api-key",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_document"
    assert preview["payload"]["name"] == "Test Document"
    assert preview["payload"]["recipients"][0]["email"] == "test@example.com"


def test_successful_list_documents():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"results": [{"id": "doc1", "name": "Document 1"}]},
        )
    )

    result = pandadoc.main(
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["results"][0]["id"] == "doc1"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_successful_get_document():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"id": "doc123", "name": "Test Doc", "status": "draft"},
        )
    )

    result = pandadoc.main(
        operation="get_document",
        document_id="doc123",
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "doc123"
    assert "doc123" in fake_client.calls[0][1]


def test_successful_create_document():
    fake_client = FakeClient(
        response=DummyResponse(
            201,
            {"id": "new-doc", "status": "document.draft"},
        )
    )

    result = pandadoc.main(
        operation="create_document",
        name="Test Document",
        template_uuid="template123",
        recipient_email="test@example.com",
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "new-doc"
    assert fake_client.calls[0][0] == "POST"


def test_successful_send_document():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"id": "doc123", "status": "document.sent"},
        )
    )

    result = pandadoc.main(
        operation="send_document",
        document_id="doc123",
        message="Please sign",
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["id"] == "doc123"
    assert fake_client.calls[0][0] == "POST"


def test_download_document_returns_binary():
    fake_client = FakeClient(
        response=DummyResponse(200, {})
    )

    result = pandadoc.main(
        operation="download_document",
        document_id="doc123",
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert "document" in result["output"]
    assert result["output"]["content_type"] == "application/pdf"


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400,
            {"detail": "Invalid request parameters"},
        )
    )

    result = pandadoc.main(
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Connection failed"))

    result = pandadoc.main(
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Connection failed" in result["output"]["details"]


def test_invalid_json_response():
    fake_client = FakeClient(
        response=DummyResponse(200, ValueError("Invalid JSON"), text="Not JSON")
    )

    result = pandadoc.main(
        PANDADOC_API_KEY="api-key",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
