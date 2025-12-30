"""Tests for OAuthManager utilities."""

import time
from typing import Any, Dict, Optional

import pytest

from server_utils.external_api import OAuthManager, OAuthTokens


class FakeResponse:
    def __init__(self, status_code: int, json_data: Dict[str, Any]):
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"HTTP error {self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self._json_data


class FakeClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.recorded_data: Optional[Dict[str, Any]] = None

    def post(self, url: str, *, data: Dict[str, Any]) -> FakeResponse:  # type: ignore[override]
        self.recorded_data = {"url": url, "data": data}
        return self.response


@pytest.fixture
def token_url() -> str:
    return "https://example.com/token"


def test_returns_cached_token_when_not_expired(token_url: str) -> None:
    manager = OAuthManager(
        token_url=token_url,
        client_id="cid",
        client_secret="secret",
    )
    manager.set_tokens(
        OAuthTokens(
            access_token="cached", expires_at=time.time() + 1000, refresh_token="r1"
        )
    )

    token, refreshed = manager.get_access_token()

    assert token == "cached"
    assert refreshed is None


def test_refreshes_token_when_expired(token_url: str) -> None:
    response = FakeResponse(200, {"access_token": "new", "expires_in": 600})
    client = FakeClient(response)
    manager = OAuthManager(
        token_url=token_url,
        client_id="cid",
        client_secret="secret",
        scopes=["read", "write"],
        http_client=client,
    )
    manager.set_tokens(
        OAuthTokens(access_token="old", refresh_token="refresh", expires_at=0)
    )

    token, new_tokens = manager.get_access_token()

    assert token == "new"
    assert new_tokens is not None
    assert new_tokens.refresh_token == "refresh"
    assert client.recorded_data == {
        "url": token_url,
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": "refresh",
            "client_id": "cid",
            "client_secret": "secret",
            "scope": "read write",
        },
    }


def test_refresh_uses_explicit_refresh_token(token_url: str) -> None:
    response = FakeResponse(200, {"access_token": "explicit", "expires_in": 120})
    client = FakeClient(response)
    manager = OAuthManager(
        token_url=token_url,
        client_id="cid",
        client_secret="secret",
        http_client=client,
    )

    token, new_tokens = manager.get_access_token(refresh_token="fresh")

    assert token == "explicit"
    assert new_tokens is not None
    assert new_tokens.refresh_token == "fresh"


def test_get_auth_header_includes_token_type(token_url: str) -> None:
    manager = OAuthManager(token_url=token_url, client_id="cid", client_secret="secret")
    manager.set_tokens(
        OAuthTokens(access_token="cached", token_type="Token", expires_at=time.time() + 1000)
    )

    headers, refreshed = manager.get_auth_header()

    assert headers == {"Authorization": "Token cached"}
    assert refreshed is None


def test_errors_when_no_tokens_available(token_url: str) -> None:
    manager = OAuthManager(token_url=token_url, client_id="cid", client_secret="secret")

    with pytest.raises(ValueError):
        manager.get_access_token()
