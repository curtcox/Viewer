import pytest
import jwt

from server_utils.external_api.google_auth import GoogleAuthManager
from server_utils.external_api.microsoft_auth import MicrosoftAuthManager


import requests


class StubResponse:
    def __init__(self, json_payload, status_code=200, text=""):
        self._json_payload = json_payload
        self.status_code = status_code
        self.text = text
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._json_payload, Exception):
            raise self._json_payload
        return self._json_payload


class StubClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, data=None, **kwargs):
        self.calls.append({"url": url, "data": data, "kwargs": kwargs})
        return self.response


class RaisingClient:
    def __init__(self, exc):
        self.exc = exc

    def post(self, url, data=None, **kwargs):  # pragma: no cover - exercised in tests
        raise self.exc


def test_google_service_account_success(monkeypatch):
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({"access_token": "abc", "expires_in": 3600})))
    token = manager.get_access_token(
        {
            "client_email": "svc@example.com",
            "private_key": "secret",
            "algorithm": "HS256",
        },
        scopes=["https://www.googleapis.com/auth/userinfo.email"],
    )

    assert token["access_token"] == "abc"


def test_google_missing_field_returns_error():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({})))
    token = manager.get_access_token({}, scopes=["scope"])

    assert token["output"]["error"]["type"] == "validation_error"
    assert token["output"]["error"]["details"]["field"] == "client_email"


def test_google_invalid_json_response():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse(ValueError("boom"), status_code=200)))
    token = manager.get_access_token(
        {"client_email": "svc@example.com", "private_key": "secret", "algorithm": "HS256"},
        scopes=["scope"],
    )

    assert token["output"]["error"] == "Invalid JSON response from Google token endpoint"


def test_google_service_account_subject_adds_sub_claim():
    stub_client = StubClient(StubResponse({"access_token": "abc", "expires_in": 3600}))
    manager = GoogleAuthManager(http_client=stub_client)

    token = manager.get_access_token(
        {
            "client_email": "svc@example.com",
            "private_key": "secret",
            "algorithm": "HS256",
        },
        scopes=["scope"],
        subject="user@example.com",
    )

    assertion = stub_client.calls[0]["data"]["assertion"]
    decoded = jwt.decode(assertion, "secret", algorithms=["HS256"], options={"verify_aud": False})

    assert token["access_token"] == "abc"
    assert decoded["sub"] == "user@example.com"


def test_google_service_account_rejects_empty_subject():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({"access_token": "abc"})))

    token = manager.get_access_token(
        {"client_email": "svc@example.com", "private_key": "secret", "algorithm": "HS256"},
        scopes=["scope"],
        subject="",
    )

    assert token["output"]["error"]["details"]["field"] == "subject"


def test_google_service_account_custom_token_uri_is_used():
    stub_client = StubClient(StubResponse({"access_token": "abc", "expires_in": 3600}))
    manager = GoogleAuthManager(http_client=stub_client)

    manager.get_access_token(
        {"client_email": "svc@example.com", "private_key": "secret", "algorithm": "HS256"},
        scopes=["scope"],
        token_uri="https://custom/token",
    )

    assert stub_client.calls[0]["url"] == "https://custom/token"


def test_google_missing_scopes_returns_validation_error():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({})))

    token = manager.get_access_token(
        {"client_email": "svc@example.com", "private_key": "secret", "algorithm": "HS256"},
        scopes=[],
    )

    assert token["output"]["error"]["type"] == "validation_error"
    assert token["output"]["error"]["details"]["field"] == "scopes"


def test_google_request_exception_returns_structured_error():
    exc = requests.RequestException("boom")
    exc.response = type("Resp", (), {"status_code": 503})()
    manager = GoogleAuthManager(http_client=RaisingClient(exc))

    token = manager.get_access_token(
        {"client_email": "svc@example.com", "private_key": "secret", "algorithm": "HS256"},
        scopes=["scope"],
    )

    assert token["output"]["error"] == "Google token request failed"
    assert token["output"].get("status_code") == 503


def test_google_oauth_refresh_success():
    stub_client = StubClient(StubResponse({"access_token": "oauth_token", "token_type": "Bearer"}))
    manager = GoogleAuthManager(http_client=stub_client)

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=["scope1", "scope2"],
    )

    assert token["access_token"] == "oauth_token"
    assert stub_client.calls[0]["data"]["grant_type"] == "refresh_token"
    assert stub_client.calls[0]["data"]["scope"] == "scope1 scope2"


def test_google_oauth_refresh_missing_inputs():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({})))

    token = manager.refresh_oauth_token(
        refresh_token="",
        client_id="client",
        client_secret="secret",
        scopes=["scope"],
    )

    assert token["output"]["error"]["details"]["field"] == "refresh_token"


def test_google_oauth_refresh_missing_scopes_returns_error():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({})))

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=[],
    )

    assert token["output"]["error"]["details"]["field"] == "scopes"


def test_google_oauth_refresh_request_exception():
    exc = requests.RequestException("oauth_down")
    exc.response = type("Resp", (), {"status_code": 502})()
    manager = GoogleAuthManager(http_client=RaisingClient(exc))

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=["scope"],
    )

    assert token["output"]["error"] == "Google OAuth token request failed"
    assert token["output"]["status_code"] == 502


def test_google_oauth_refresh_error_response():
    manager = GoogleAuthManager(
        http_client=StubClient(StubResponse({}, status_code=400, text="bad request"))
    )

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=["scope"],
    )

    assert token["output"]["error"]["type"] == "api_error"
    assert token["output"]["error"]["status_code"] == 400


def test_google_oauth_refresh_invalid_json():
    manager = GoogleAuthManager(
        http_client=StubClient(StubResponse(ValueError("boom"), status_code=200, text="oops"))
    )

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=["scope"],
    )

    assert token["output"]["error"] == "Invalid JSON response from Google OAuth token endpoint"


def test_google_oauth_refresh_missing_access_token():
    manager = GoogleAuthManager(http_client=StubClient(StubResponse({"expires_in": 1000}, status_code=200)))

    token = manager.refresh_oauth_token(
        refresh_token="refresh_me",
        client_id="client",
        client_secret="secret",
        scopes=["scope"],
    )

    assert token["output"]["error"] == "Token response missing access_token"


def test_microsoft_client_credentials_success():
    stub_client = StubClient(StubResponse({"access_token": "graph_token", "token_type": "Bearer"}))
    manager = MicrosoftAuthManager(http_client=stub_client)
    token = manager.get_access_token("tenant", "client", "secret", scopes=["scope/.default"])

    assert token["access_token"] == "graph_token"
    assert stub_client.calls[0]["data"]["grant_type"] == "client_credentials"


def test_microsoft_missing_secret():
    manager = MicrosoftAuthManager(http_client=StubClient(StubResponse({})))
    token = manager.get_access_token("", "client", "secret", scopes=["scope"])

    assert token["output"]["error"]["type"] == "validation_error"
    assert token["output"]["error"]["details"]["field"] == "tenant_id"


def test_microsoft_error_response():
    manager = MicrosoftAuthManager(http_client=StubClient(StubResponse({}, status_code=500, text="bad")))
    token = manager.get_access_token("tenant", "client", "secret", scopes=["scope"])

    assert token["output"]["error"]["status_code"] == 500
    assert token["output"]["error"]["type"] == "api_error"


def test_microsoft_missing_scopes_returns_validation_error():
    manager = MicrosoftAuthManager(http_client=StubClient(StubResponse({})))

    token = manager.get_access_token("tenant", "client", "secret", scopes=[])

    assert token["output"]["error"]["type"] == "validation_error"
    assert token["output"]["error"]["details"]["field"] == "scopes"


def test_microsoft_request_exception_returns_structured_error():
    exc = requests.RequestException("down")
    exc.response = type("Resp", (), {"status_code": 504})()
    manager = MicrosoftAuthManager(http_client=RaisingClient(exc))

    token = manager.get_access_token("tenant", "client", "secret", scopes=["scope"])

    assert token["output"]["error"] == "Microsoft token request failed"
    assert token["output"].get("status_code") == 504
