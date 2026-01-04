import requests
from typing import Any

from reference.templates.servers.definitions import smartsheet


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
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


def test_missing_access_token_returns_auth_error():
    result = smartsheet.main(dry_run=False)

    assert result["output"]["error"] == "Missing SMARTSHEET_ACCESS_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = smartsheet.main(operation="unknown", SMARTSHEET_ACCESS_TOKEN="token")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_missing_required_fields():
    missing_sheet = smartsheet.main(operation="get_sheet", SMARTSHEET_ACCESS_TOKEN="token")
    missing_row = smartsheet.main(operation="get_row", SMARTSHEET_ACCESS_TOKEN="token")
    missing_rows_data = smartsheet.main(operation="add_rows", sheet_id="123", SMARTSHEET_ACCESS_TOKEN="token")

    assert missing_sheet["output"]["error"]["message"] == "Missing required sheet_id"
    assert missing_row["output"]["error"]["message"] == "Missing required row_id"
    assert missing_rows_data["output"]["error"]["message"] == "Missing required rows_data"


def test_dry_run_preview_for_list_sheets():
    result = smartsheet.main(operation="list_sheets", SMARTSHEET_ACCESS_TOKEN="token")

    preview = result["output"]["preview"]
    assert preview["operation"] == "list_sheets"
    assert "smartsheet.com" in preview["url"]
    assert preview["method"] == "GET"


def test_dry_run_preview_for_add_rows():
    result = smartsheet.main(
        operation="add_rows",
        sheet_id="123",
        rows_data='[{"cells": [{"columnId": 1, "value": "test"}]}]',
        SMARTSHEET_ACCESS_TOKEN="token",
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "add_rows"
    assert preview["method"] == "POST"
    assert isinstance(preview["payload"], list)


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = smartsheet.main(
        operation="list_sheets",
        SMARTSHEET_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Smartsheet request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=200, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = smartsheet.main(
        operation="list_sheets",
        SMARTSHEET_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 200


def test_api_error_returns_message_and_status():
    response = DummyResponse(status_code=400, json_data={"message": "Bad request"})
    client = FakeClient(response=response)

    result = smartsheet.main(
        operation="list_sheets",
        SMARTSHEET_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Bad request"
    assert result["output"]["status_code"] == 400


def test_success_returns_data():
    payload = {"data": [{"id": "1", "name": "Sheet 1"}]}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = smartsheet.main(
        operation="list_sheets",
        SMARTSHEET_ACCESS_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    assert client.calls[0][0] == "GET"


def test_invalid_rows_data_json():
    result = smartsheet.main(
        operation="add_rows",
        sheet_id="123",
        rows_data="not json",
        SMARTSHEET_ACCESS_TOKEN="token",
    )

    assert result["output"]["error"]["message"] == "Invalid rows_data JSON format"
