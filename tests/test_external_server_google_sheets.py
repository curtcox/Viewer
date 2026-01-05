import json
from typing import Any, Dict

import pytest
import requests

from reference.templates.servers.definitions import google_sheets


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self.ok = status_code < 400

    def json(self) -> Any:
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FakeClient:
    def __init__(self, response: Any = None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, str, Dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> Any:
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

    def get(self, url: str, **kwargs: Any) -> Any:
        self.calls.append(("GET", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response


class FakeAuthManager:
    def __init__(self, result: Dict[str, Any]):
        self.result = result
        self.calls: list[Dict[str, Any]] = []

    def get_authorization(self, info: Dict[str, Any], scopes, subject=None):
        self.calls.append({"info": info, "scopes": list(scopes), "subject": subject})
        return self.result


def test_missing_spreadsheet_or_range_returns_validation_error():
    missing_sheet = google_sheets.main(spreadsheet_id="", range_name="Sheet1!A1:B2")
    missing_range = google_sheets.main(spreadsheet_id="sheet123", range_name="")

    assert missing_sheet["output"]["error"]["message"] == "Missing required spreadsheet_id"
    assert missing_range["output"]["error"]["message"] == "Missing required range_name"


def test_missing_credentials_returns_error():
    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        access_token="",
        service_account_json="",
        dry_run=False,
    )

    assert result["output"]["error"] == "Missing Google credentials"
    assert result["output"]["status_code"] == 401


def test_invalid_service_account_json_returns_error():
    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        service_account_json="not-json",
        dry_run=False,
    )

    assert result["output"]["error"]["message"] == "Invalid GOOGLE_SERVICE_ACCOUNT_JSON"
    assert result["output"]["error"]["type"] == "validation_error"


def test_dry_run_shows_preview_without_calling_api():
    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        access_token="token",
        operation="append",
        values=[["a", "b"]],
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "append"
    assert preview["method"] == "POST"
    assert preview["auth"] == "access_token"
    assert preview["params"] == {"valueInputOption": "RAW"}
    assert preview["payload"] == {"values": [["a", "b"]]}


def test_append_requires_valid_values_json():
    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        operation="append",
        values="not-json",
        dry_run=False,
        access_token="token",
    )

    assert result["output"]["error"]["message"] == "Values must be valid JSON"


def test_append_rejects_non_row_sequences():
    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        operation="append",
        values=["a", "b"],
        dry_run=False,
        access_token="token",
    )

    assert result["output"]["error"]["message"] == "Each row must be a list of values"


def test_read_with_service_account_uses_auth_manager_and_returns_payload():
    dummy_response = DummyResponse(status_code=200, json_data={"values": [["1", "2"]]})
    auth_manager = FakeAuthManager({"headers": {"Authorization": "Bearer fake"}})

    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        service_account_json=json.dumps({"client_email": "x", "private_key": "y"}),
        dry_run=False,
        client=FakeClient(dummy_response),
        auth_manager=auth_manager,
    )

    assert auth_manager.calls[0]["scopes"] == ["https://www.googleapis.com/auth/spreadsheets"]
    assert result["output"] == {"values": [["1", "2"]]}


def test_append_posts_rows_and_handles_api_errors():
    api_error = {"error": {"message": "permission denied"}}
    dummy_response = DummyResponse(status_code=403, json_data=api_error)

    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        operation="append",
        values=[["a"]],
        dry_run=False,
        access_token="token",
        client=FakeClient(dummy_response),
    )

    assert result["output"]["error"] == api_error["error"]
    assert result["output"]["status_code"] == 403


def test_request_exceptions_include_status(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(status_code=504)
    exc = requests.RequestException("timeout")
    exc.response = dummy_response

    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        access_token="token",
        dry_run=False,
        client=FakeClient(exc=exc),
    )

    assert result["output"]["error"] == "Google Sheets request failed"
    assert result["output"]["status_code"] == 504
    assert "timeout" in result["output"]["details"]


def test_invalid_json_response_returns_error():
    dummy_response = DummyResponse(status_code=502, json_data=ValueError("boom"), text="<!>")

    result = google_sheets.main(
        spreadsheet_id="sheet123",
        range_name="Sheet1!A1:B2",
        access_token="token",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 502
    assert result["output"]["details"] == "<!>"
