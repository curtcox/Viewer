from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

import server_execution
from app import app
from text_function_runner import run_text_function

TEMPLATE_PATH = Path("reference_templates/servers/definitions/proxy.py")


@pytest.fixture()
def proxy_template_code():
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _set_base_url(template_code: str, new_url: str) -> str:
    placeholder = "BASE_TARGET_URL = PLACEHOLDER_TARGET_URL"
    replacement = f'BASE_TARGET_URL = "{new_url}"'
    assert placeholder in template_code
    return template_code.replace(placeholder, replacement)


def test_proxy_template_forwards_request(monkeypatch, proxy_template_code):
    code = _set_base_url(proxy_template_code, "https://foo.service-now.com/api")

    captured = {}

    def fake_request(
        method, url, *, headers=None, data=None, allow_redirects=True, timeout=None
    ):
        captured.update(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "data": data,
                "allow_redirects": allow_redirects,
                "timeout": timeout,
            }
        )
        return SimpleNamespace(
            content=b"proxied", headers={"Content-Type": "application/json"}
        )

    monkeypatch.setattr(requests, "request", fake_request)

    with app.test_request_context(
        "/servicenow/more/path/info?q=stuff",
        method="POST",
        data=b'{"hello": "world"}',
        headers={"Content-Type": "application/json", "X-Test": "abc"},
        base_url="https://viewer.example",
    ):
        details = server_execution.request_details()
        assert "Content-Length" in details["headers"]
        assert "Host" in details["headers"]

        payload = {
            "context": {"variables": {}, "secrets": {}, "servers": {}},
            "request": details,
        }
        result = run_text_function(code, payload)

    assert captured["method"] == "POST"
    assert captured["url"] == "https://foo.service-now.com/api/more/path/info?q=stuff"
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == 60
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["headers"]["X-Test"] == "abc"
    assert "Host" not in captured["headers"]
    assert "Content-Length" not in captured["headers"]
    assert captured["data"] == b'{"hello": "world"}'
    assert result["output"] == b"proxied"
    assert result["content_type"] == "application/json"


def test_proxy_template_requires_configuration(monkeypatch, proxy_template_code):
    def fail_request(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("Proxy attempted an HTTP request without configuration")

    monkeypatch.setattr(requests, "request", fail_request)

    with app.test_request_context("/servicenow"):
        payload = {
            "context": {"variables": {}, "secrets": {}, "servers": {}},
            "request": server_execution.request_details(),
        }
        result = run_text_function(proxy_template_code, payload)

    assert "Configure BASE_TARGET_URL" in result["output"]
    assert result["content_type"] == "text/plain"


def test_proxy_template_handles_root_paths(monkeypatch, proxy_template_code):
    code = _set_base_url(proxy_template_code, "https://foo.service-now.com/api")

    captured = {}

    def fake_request(
        method, url, *, headers=None, data=None, allow_redirects=True, timeout=None
    ):
        captured["url"] = url
        return SimpleNamespace(content=b"root", headers={"Content-Type": "text/plain"})

    monkeypatch.setattr(requests, "request", fake_request)

    with app.test_request_context("/servicenow/", base_url="https://viewer.example"):
        payload = {
            "context": {"variables": {}, "secrets": {}, "servers": {}},
            "request": server_execution.request_details(),
        }
        result = run_text_function(code, payload)

    assert captured["url"] == "https://foo.service-now.com/api/"
    assert result["output"] == b"root"
    assert result["content_type"] == "text/plain"


def test_proxy_template_uses_global_variable_configuration(
    monkeypatch, proxy_template_code
):
    captured = {}

    def fake_request(
        method, url, *, headers=None, data=None, allow_redirects=True, timeout=None
    ):
        captured.update({"method": method, "url": url})
        return SimpleNamespace(
            content=b"configured", headers={"Content-Type": "application/json"}
        )

    monkeypatch.setattr(requests, "request", fake_request)

    with app.test_request_context(
        "/servicenow/tasks", method="GET", base_url="https://viewer.example"
    ):
        payload = {
            "context": {
                "variables": {"BASE_TARGET_URL": "https://foo.service-now.com/api"},
                "secrets": {},
                "servers": {},
            },
            "request": server_execution.request_details(),
        }
        result = run_text_function(proxy_template_code, payload)

    assert captured["method"] == "GET"
    assert captured["url"] == "https://foo.service-now.com/api/tasks"
    assert result["output"] == b"configured"
    assert result["content_type"] == "application/json"


def test_proxy_template_supports_server_specific_variable(
    monkeypatch, proxy_template_code
):
    captured = {}

    def fake_request(
        method, url, *, headers=None, data=None, allow_redirects=True, timeout=None
    ):
        captured["url"] = url
        return SimpleNamespace(
            content=b"specific", headers={"Content-Type": "text/plain"}
        )

    monkeypatch.setattr(requests, "request", fake_request)

    with app.test_request_context(
        "/service-now/tickets", method="GET", base_url="https://viewer.example"
    ):
        payload = {
            "context": {
                "variables": {
                    "SERVICE_NOW_BASE_TARGET_URL": "https://foo.service-now.com/api"
                },
                "secrets": {},
                "servers": {},
            },
            "request": server_execution.request_details(),
        }
        run_text_function(proxy_template_code, payload)

    assert captured["url"] == "https://foo.service-now.com/api/tickets"
