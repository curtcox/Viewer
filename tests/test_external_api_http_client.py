"""Unit tests for the ExternalApiClient HTTP helper."""

from typing import Any, Dict

import logging
import pytest
from requests import RequestException, Response

from server_utils.external_api.http_client import ExternalApiClient, HttpClientConfig


class DummyResponse(Response):
    def __init__(self, status_code: int = 200):
        super().__init__()
        self.status_code = status_code


class DummySession:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []
        self.to_raise: RequestException | None = None
        self.response = DummyResponse()

    def request(self, **kwargs: Any) -> DummyResponse:
        self.calls.append(kwargs)
        if self.to_raise:
            raise self.to_raise
        return self.response

    def mount(self, *_: Any, **__: Any) -> None:  # pragma: no cover - unused in tests
        return None


def test_request_uses_defaults_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    session = DummySession()
    client = ExternalApiClient(HttpClientConfig(timeout=5), session=session)

    with caplog.at_level(logging.INFO):
        response = client.get("https://example.test", params={"q": "x"})

    assert response.status_code == 200
    assert session.calls == [
        {
            "method": "GET",
            "url": "https://example.test",
            "headers": None,
            "json": None,
            "data": None,
            "params": {"q": "x"},
            "timeout": 5,
        }
    ]
    assert "API Request: GET https://example.test" in caplog.text
    assert "API Response: GET https://example.test -> 200" in caplog.text


def test_request_uses_provided_timeout(caplog: pytest.LogCaptureFixture) -> None:
    session = DummySession()
    client = ExternalApiClient(HttpClientConfig(timeout=1), session=session)

    with caplog.at_level(logging.INFO):
        client.post("https://example.test", timeout=10)

    assert session.calls[0]["timeout"] == 10
    assert "API Request: POST https://example.test" in caplog.text


def test_request_logs_and_raises_request_exception(caplog: pytest.LogCaptureFixture) -> None:
    session = DummySession()
    exc = RequestException("boom")
    session.to_raise = exc
    client = ExternalApiClient(session=session)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RequestException):
            client.delete("https://example.test")

    assert "API Error: DELETE https://example.test -> boom" in caplog.text


def test_request_passes_auth_parameter() -> None:
    """Test that auth parameter is correctly passed to session.request()."""
    session = DummySession()
    client = ExternalApiClient(session=session)

    client.get("https://example.test", auth=("user", "pass"))

    assert session.calls == [
        {
            "method": "GET",
            "url": "https://example.test",
            "headers": None,
            "json": None,
            "data": None,
            "params": None,
            "timeout": 60,
            "auth": ("user", "pass"),
        }
    ]
