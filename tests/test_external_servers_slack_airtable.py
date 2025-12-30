"""Unit tests for Slack and Airtable server definitions."""

from typing import Any
import pytest
import requests

from reference_templates.servers.definitions import airtable, slack


class FakeClient:
    def __init__(self, response: Any = None, *, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, str]] = []

    def post(self, url: str, **_: Any) -> Any:
        self.calls.append(("POST", url))
        if self.exc:
            raise self.exc
        return self.response

    def get(self, url: str, **_: Any) -> Any:
        self.calls.append(("GET", url))
        if self.exc:
            raise self.exc
        return self.response


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text

    def json(self) -> Any:
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def test_slack_missing_token_returns_error():
    result = slack.main(text="hi", channel="#demo", SLACK_BOT_TOKEN="", dry_run=False)

    assert "error" in result["output"]
    assert result["output"]["status_code"] == 401


def test_slack_dry_run_preview():
    result = slack.main(text="hi", channel="#demo", SLACK_BOT_TOKEN="xoxb-123")

    assert result["output"]["preview"] == {"channel": "#demo", "text": "hi"}
    assert "Dry run" in result["output"]["message"]


def test_slack_api_error_includes_status(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(
        status_code=400, json_data={"ok": False, "error": "invalid_auth"}
    )

    result = slack.main(
        text="hi",
        channel="#demo",
        SLACK_BOT_TOKEN="token",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"]["error"] == "invalid_auth"
    assert result["output"]["status_code"] == 400
    assert result["output"]["response"] == {"ok": False, "error": "invalid_auth"}


def test_slack_request_exception_carries_status(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(status_code=503, json_data={})

    exc = requests.RequestException("network down")
    exc.response = dummy_response

    result = slack.main(
        text="hi",
        channel="#demo",
        SLACK_BOT_TOKEN="token",
        dry_run=False,
        client=FakeClient(exc=exc),
    )

    assert result["output"]["error"] == "Slack request failed"
    assert result["output"]["status_code"] == 503
    assert "network down" in result["output"]["details"]


def test_slack_invalid_json_returns_error(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(status_code=502, json_data=ValueError("boom"), text="<!>" )

    result = slack.main(
        text="hi",
        channel="#demo",
        SLACK_BOT_TOKEN="token",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 502
    assert result["output"]["details"] == "<!>"


def test_slack_success_returns_api_payload(monkeypatch: pytest.MonkeyPatch):
    api_payload = {"ok": True, "ts": "123.456", "channel": "C1"}
    dummy_response = DummyResponse(status_code=200, json_data=api_payload)

    result = slack.main(
        text="hi",
        channel="#demo",
        SLACK_BOT_TOKEN="token",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"] == api_payload


def test_airtable_missing_credentials_and_parameters():
    missing_key = airtable.main(base_id="", table_name="", AIRTABLE_API_KEY="")
    missing_table = airtable.main(
        base_id="app123", table_name="", AIRTABLE_API_KEY="key123"
    )

    assert missing_key["output"]["status_code"] == 401
    assert missing_table["output"]["status_code"] == 400


def test_airtable_dry_run_lists_with_preview():
    result = airtable.main(
        base_id="app123", table_name="Tasks", AIRTABLE_API_KEY="key123", max_records=2
    )

    preview = result["output"]["preview"]
    assert preview["operation"] == "list"
    assert preview["url"].endswith("app123/Tasks")
    assert preview["params"] == {"maxRecords": 2}


def test_airtable_create_invalid_json_returns_error():
    result = airtable.main(
        base_id="app123",
        table_name="Tasks",
        AIRTABLE_API_KEY="key123",
        operation="create",
        record="not-json",
        dry_run=False,
    )

    assert result["output"]["error"] == "Invalid record JSON for create operation"
    assert result["output"]["status_code"] == 400


def test_airtable_retrieve_requires_record_id():
    result = airtable.main(
        base_id="app123",
        table_name="Tasks",
        AIRTABLE_API_KEY="key123",
        operation="retrieve",
        record_id="",
        dry_run=False,
    )

    assert "record_id required" in result["output"]["error"]
    assert result["output"]["status_code"] == 400


def test_airtable_api_errors_are_returned(monkeypatch: pytest.MonkeyPatch):
    api_error = {"error": {"type": "AUTHENTICATION_REQUIRED"}}
    dummy_response = DummyResponse(status_code=401, json_data=api_error)

    result = airtable.main(
        base_id="app123",
        table_name="Tasks",
        AIRTABLE_API_KEY="key123",
        operation="retrieve",
        record_id="rec123",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"]["status_code"] == 401
    assert result["output"]["response"] == api_error


def test_airtable_request_exception_includes_status(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(status_code=504)

    exc = requests.RequestException("timeout")
    exc.response = dummy_response

    result = airtable.main(
        base_id="app123",
        table_name="Tasks",
        AIRTABLE_API_KEY="key123",
        operation="list",
        dry_run=False,
        client=FakeClient(exc=exc),
    )

    assert result["output"]["error"] == "Airtable request failed"
    assert result["output"]["status_code"] == 504
    assert "timeout" in result["output"]["details"]


def test_airtable_invalid_json_response(monkeypatch: pytest.MonkeyPatch):
    dummy_response = DummyResponse(status_code=502, json_data=ValueError("boom"), text="bad html")

    result = airtable.main(
        base_id="app123",
        table_name="Tasks",
        AIRTABLE_API_KEY="key123",
        operation="list",
        dry_run=False,
        client=FakeClient(dummy_response),
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 502
    assert result["output"]["details"] == "bad html"
