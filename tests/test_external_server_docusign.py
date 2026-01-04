from __future__ import annotations

import requests

from reference.templates.servers.definitions import docusign


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


def test_requires_access_token():
    result = docusign.main(DOCUSIGN_ACCOUNT_ID="account123")

    assert result["output"]["error"] == "Missing DOCUSIGN_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_requires_account_id():
    result = docusign.main(DOCUSIGN_ACCESS_TOKEN="token")

    assert result["output"]["error"] == "Missing DOCUSIGN_ACCOUNT_ID"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = docusign.main(
        operation="unknown",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_get_envelope_requires_id():
    result = docusign.main(
        operation="get_envelope",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required envelope_id"


def test_create_envelope_requires_subject():
    result = docusign.main(
        operation="create_envelope",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required email_subject"


def test_create_envelope_requires_recipient_email():
    result = docusign.main(
        operation="create_envelope",
        email_subject="Test",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required recipient_email"


def test_create_envelope_requires_recipient_name():
    result = docusign.main(
        operation="create_envelope",
        email_subject="Test",
        recipient_email="test@example.com",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required recipient_name"


def test_get_template_requires_id():
    result = docusign.main(
        operation="get_template",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required template_id"


def test_download_document_requires_envelope_id():
    result = docusign.main(
        operation="download_document",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    assert result["output"]["error"]["message"] == "Missing required envelope_id"


def test_dry_run_preview_for_list_envelopes():
    result = docusign.main(
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        status="sent",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "GET"
    assert preview["operation"] == "list_envelopes"
    assert preview["params"]["status"] == "sent"
    assert "account123" in preview["url"]


def test_dry_run_preview_for_create_envelope():
    result = docusign.main(
        operation="create_envelope",
        email_subject="Test Document",
        recipient_email="test@example.com",
        recipient_name="John Doe",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_envelope"
    assert preview["payload"]["emailSubject"] == "Test Document"
    assert preview["payload"]["recipients"]["signers"][0]["email"] == "test@example.com"


def test_successful_list_envelopes():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"envelopes": [{"envelopeId": "env1", "status": "sent"}]},
        )
    )

    result = docusign.main(
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["envelopes"][0]["envelopeId"] == "env1"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0] == "GET"


def test_successful_get_envelope():
    fake_client = FakeClient(
        response=DummyResponse(
            200,
            {"envelopeId": "env123", "status": "sent", "emailSubject": "Test"},
        )
    )

    result = docusign.main(
        operation="get_envelope",
        envelope_id="env123",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["envelopeId"] == "env123"
    assert "env123" in fake_client.calls[0][1]


def test_successful_create_envelope():
    fake_client = FakeClient(
        response=DummyResponse(
            201,
            {"envelopeId": "new-env", "status": "sent"},
        )
    )

    result = docusign.main(
        operation="create_envelope",
        email_subject="Test Document",
        recipient_email="test@example.com",
        recipient_name="John Doe",
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert result["output"]["envelopeId"] == "new-env"
    assert fake_client.calls[0][0] == "POST"


def test_api_error_handling():
    fake_client = FakeClient(
        response=DummyResponse(
            400,
            {"errorCode": "INVALID_REQUEST", "message": "Bad request"},
        )
    )

    result = docusign.main(
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 400


def test_request_exception_handling():
    fake_client = FakeClient(exc=requests.RequestException("Connection failed"))

    result = docusign.main(
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Connection failed" in result["output"]["details"]


def test_invalid_json_response():
    fake_client = FakeClient(
        response=DummyResponse(200, ValueError("Invalid JSON"), text="Not JSON")
    )

    result = docusign.main(
        DOCUSIGN_ACCESS_TOKEN="token",
        DOCUSIGN_ACCOUNT_ID="account123",
        dry_run=False,
        client=fake_client,
    )

    assert "error" in result["output"]
    assert "Invalid JSON response" in result["output"]["error"]
