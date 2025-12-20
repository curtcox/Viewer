from __future__ import annotations

import json
import threading
import urllib.parse
from queue import Queue

import requests

from server_execution.external_call_tracking import (
    capture_external_calls,
    sanitize_external_calls,
)


def test_capture_and_sanitize_external_calls(monkeypatch):
    secret_value = "super-secret"

    encoded_secret = urllib.parse.quote_plus(secret_value)

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = f"body {secret_value}".encode("utf-8")
        response.headers = {"Authorization": f"Bearer {secret_value}"}
        response.url = f"{url}?token={encoded_secret}"
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
    assert entry["response"]["url"].endswith("token=<secret:API_KEY>")

    json.dumps(sanitized)  # Ensure JSON serializable


def test_capture_is_thread_local(monkeypatch):
    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        response.headers = {}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    barrier = threading.Barrier(2)
    results: Queue[tuple[str, list[dict[str, object]]]] = Queue()

    def _worker(name: str):
        with capture_external_calls() as call_log:
            barrier.wait()
            requests.Session().get(f"https://example.com/{name}")
        results.put((name, list(call_log)))

    threads = [
        threading.Thread(target=_worker, args=(label,)) for label in ("one", "two")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    collected: dict[str, list[dict[str, object]]] = {}
    while not results.empty():
        name, log = results.get()
        collected[name] = log
    assert len(collected.get("one", [])) == 1
    assert len(collected.get("two", [])) == 1
    assert collected["one"][0]["request"]["url"].endswith("/one")
    assert collected["two"][0]["request"]["url"].endswith("/two")


def test_nested_captures_propagate_to_outer(monkeypatch):
    """Test that nested captures propagate calls to outer captures.

    This is important for scenarios like test fixtures that wrap code
    that also uses capture_external_calls (e.g., code_execution.py).
    """

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        response.headers = {}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    # Outer capture (simulates test fixture)
    with capture_external_calls() as outer_log:
        # Inner capture (simulates code_execution.py)
        with capture_external_calls() as inner_log:
            requests.Session().get("https://example.com/api")

        # Inner capture should have the call
        assert len(inner_log) == 1
        assert inner_log[0]["request"]["url"] == "https://example.com/api"

    # Outer capture should ALSO have the call (propagation)
    assert len(outer_log) == 1
    assert outer_log[0]["request"]["url"] == "https://example.com/api"


def test_nested_captures_independent_records(monkeypatch):
    """Test that nested captures get independent copies of records."""

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        response.headers = {}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    with capture_external_calls() as outer_log:
        with capture_external_calls() as inner_log:
            requests.Session().get("https://example.com/api")

    # Modifying one should not affect the other (deep copy)
    outer_log[0]["request"]["url"] = "modified"
    assert inner_log[0]["request"]["url"] == "https://example.com/api"
