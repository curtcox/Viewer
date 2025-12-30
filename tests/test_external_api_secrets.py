"""Tests for secret validation utilities."""

from typing import Dict

import pytest

from server_utils.external_api import api_error, validate_api_key_with_endpoint, validate_secret


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class StubRequests:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.called_with: Dict[str, Dict[str, str]] | None = None

    def get(self, url: str, headers: Dict[str, str], timeout: int) -> FakeResponse:  # type: ignore[override]
        self.called_with = {"url": url, "headers": headers, "timeout": str(timeout)}
        return self.response


@pytest.fixture(autouse=True)
def patch_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubRequests(FakeResponse(status_code=200))
    monkeypatch.setattr("server_utils.external_api.secret_validator.requests", stub)


def test_validate_secret_missing_value_returns_error() -> None:
    result = validate_secret("", "API_KEY")

    assert result
    assert result["output"]["error"]["message"] == "Missing required secret: API_KEY"
    assert result["output"]["error"]["type"] == "auth_error"


def test_validate_secret_custom_validator_rejects() -> None:
    result = validate_secret("bad", "API_KEY", validator=lambda value: value == "good")

    assert result
    assert result["output"]["error"]["type"] == "validation_error"


def test_validate_api_key_with_endpoint_returns_none_for_success(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubRequests(FakeResponse(status_code=200))
    monkeypatch.setattr("server_utils.external_api.secret_validator.requests", stub)

    result = validate_api_key_with_endpoint(
        api_key="secret",
        validation_url="https://example.com/validate",
        headers_builder=lambda key: {"Authorization": f"Bearer {key}"},
        secret_name="CUSTOM_KEY",
    )

    assert result is None
    assert stub.called_with == {
        "url": "https://example.com/validate",
        "headers": {"Authorization": "Bearer secret"},
        "timeout": "10",
    }


def test_validate_api_key_handles_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubRequests(FakeResponse(status_code=401))
    monkeypatch.setattr("server_utils.external_api.secret_validator.requests", stub)

    result = validate_api_key_with_endpoint(
        api_key="secret",
        validation_url="https://example.com/validate",
        headers_builder=lambda key: {"Authorization": f"Bearer {key}"},
    )

    assert result == api_error("Invalid or expired API_KEY", status_code=401)


def test_validate_api_key_handles_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubRequests(FakeResponse(status_code=403))
    monkeypatch.setattr("server_utils.external_api.secret_validator.requests", stub)

    result = validate_api_key_with_endpoint(
        api_key="secret",
        validation_url="https://example.com/validate",
        headers_builder=lambda key: {"Authorization": f"Bearer {key}"},
    )

    assert result == api_error("Insufficient permissions for API_KEY", status_code=403)
