from __future__ import annotations

import json

import requests

from server_execution.external_call_tracking import capture_external_calls, sanitize_external_calls


def test_capture_and_sanitize_external_calls(monkeypatch):
    secret_value = "super-secret"

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = f"body {secret_value}".encode("utf-8")
        response.headers = {"Authorization": f"Bearer {secret_value}"}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    with capture_external_calls() as call_log:
        session = requests.Session()
        session.get(
            "https://example.com/data",
            headers={"Authorization": f"Bearer {secret_value}"},
            params={"token": secret_value},
        )

    sanitized = sanitize_external_calls(call_log, {"API_KEY": secret_value})

    assert sanitized
    entry = sanitized[0]
    assert entry["request"]["headers"]["Authorization"] == "Bearer <secret:API_KEY>"
    assert entry["request"]["params"]["token"] == "<secret:API_KEY>"
    assert entry["response"]["body"] == "body <secret:API_KEY>"

    json.dumps(sanitized)  # Ensure JSON serializable
