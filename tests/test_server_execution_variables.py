import types

import pytest
from flask import Flask, redirect

import server_execution


@pytest.fixture()
def flask_app():
    app = Flask(__name__)
    app.secret_key = "testing-secret"

    @app.route("/value")
    def value():
        return "variable-value"

    @app.route("/redirect")
    def redirect_route():
        return redirect("/value")

    return app


def test_normalize_variable_path_handles_valid_and_invalid_inputs():
    assert server_execution._normalize_variable_path("  /example  ") == "/example"
    assert server_execution._normalize_variable_path("relative") is None
    assert server_execution._normalize_variable_path(42) is None


@pytest.mark.parametrize(
    "location,current_path,expected",
    [
        ("", "/current", None),
        ("https://example.com/path", "/current", None),
        ("/next", "/current", "/next"),
        ("nested", "/current/path", "/current/nested"),
        ("/query?value=1", "/current", "/query?value=1"),
        ("next?value=2", "/current/path", "/current/next?value=2"),
    ],
)
def test_resolve_redirect_target(location, current_path, expected):
    assert server_execution._resolve_redirect_target(location, current_path) == expected


def test_fetch_variable_content_returns_route_body(flask_app, monkeypatch):
    # After decomposition, current_user is in variable_resolution module
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "current_user", types.SimpleNamespace(id="user-1"))

    with flask_app.test_request_context("/other"):
        result = server_execution._fetch_variable_content("/value")

    assert result == "variable-value"


def test_fetch_variable_content_follows_relative_redirect(flask_app, monkeypatch):
    # After decomposition, current_user is in variable_resolution module
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "current_user", types.SimpleNamespace(id="user-1"))

    with flask_app.test_request_context("/other"):
        result = server_execution._fetch_variable_content("/redirect")

    assert result == "variable-value"


def test_resolve_variable_values_prefetches_when_possible(monkeypatch):
    calls = []

    # After decomposition, patch functions in variable_resolution module where they're used
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "_should_skip_variable_prefetch", lambda: False)
    monkeypatch.setattr(
        variable_resolution,
        "_fetch_variable_content",
        lambda path: calls.append(path) or "resolved",
    )

    result = server_execution._resolve_variable_values({"foo": "/bar", "baz": "plain"})

    assert result == {"foo": "resolved", "baz": "plain"}
    assert calls == ["/bar"]


def test_resolve_variable_values_keeps_original_when_fetch_fails(monkeypatch):
    # After decomposition, patch functions in variable_resolution module where they're used
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "_should_skip_variable_prefetch", lambda: False)
    monkeypatch.setattr(variable_resolution, "_fetch_variable_content", lambda path: None)

    original = {"foo": "/bar"}
    result = server_execution._resolve_variable_values(original)

    assert result == original


def test_resolve_variable_values_returns_copy_when_prefetch_skipped(monkeypatch):
    data = {"foo": "/bar"}
    # After decomposition, patch functions in variable_resolution module where they're used
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "_should_skip_variable_prefetch", lambda: True)

    result = server_execution._resolve_variable_values(data)

    assert result == data
    assert result is not data


def test_fetch_variable_content_returns_none_without_app_context(monkeypatch):
    # After decomposition, current_user is in variable_resolution module
    from server_execution import variable_resolution
    monkeypatch.setattr(variable_resolution, "current_user", types.SimpleNamespace(id="user-1"))
    assert server_execution._fetch_variable_content("/value") is None
