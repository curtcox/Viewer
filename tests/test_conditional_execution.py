import pytest

from flask import Response

from server_execution.conditional_execution import (
    is_error,
    is_truthy,
    parse_do_segments,
    parse_if_segments,
    parse_try_segments,
    _execute_path,
)


def test_if_parsing_balances_nested_keywords():
    parts = parse_if_segments(
        ["a", "then", "if", "b", "then", "c", "else", "d", "else", "e"]
    )

    assert parts.test_path == ["a"]
    assert parts.true_path == ["if", "b", "then", "c", "else", "d"]
    assert parts.false_path == ["e"]


def test_do_parsing_detects_implicit_and_explicit():
    explicit = parse_do_segments(["echo", "value", "while", "test"])
    implicit = parse_do_segments(["echo", "value", "while"])

    assert explicit.body_path == ["echo", "value"]
    assert explicit.test_path == ["test"]
    assert not explicit.implicit_test

    assert implicit.body_path == ["echo", "value"]
    assert implicit.test_path is None
    assert implicit.implicit_test


def test_try_parsing_supports_identity_paths():
    parts = parse_try_segments(["some", "path"])
    assert parts.identity_path == ["some", "path"]


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", False),
        ("false", False),
        ("0", False),
        ("none", False),
        ("hello", True),
        ("1", True),
    ],
)
def test_truthiness_for_strings(value, expected):
    assert is_truthy(value) is expected


def test_truthiness_for_response_status():
    ok_response = Response("ok", status=200)
    error_response = Response("bad", status=404)

    assert is_truthy(ok_response)
    assert not is_truthy(error_response)


def test_error_detection_with_status_response():
    response = Response("bad", status=500)
    detected, message, status = is_error(response)

    assert detected is True
    assert message == "bad"
    assert status == 500


def test_execute_path_limits_redirect_loops(monkeypatch):
    redirect_response = Response("redirect", status=302)
    redirect_response.headers["Location"] = "/loop"

    calls: list[str] = []

    def fake_evaluate(path):
        calls.append(path)
        return redirect_response

    monkeypatch.setattr(
        "server_execution.conditional_execution.evaluate_nested", fake_evaluate
    )
    monkeypatch.setattr(
        "server_execution.conditional_execution.try_server_execution",
        lambda path: None,
    )

    output = _execute_path(["loop"], max_redirects=3)

    assert isinstance(output, tuple)
    body, status, headers = output
    assert body == "redirect"
    assert status == 302
    assert headers.get("Location") == "/loop"
    assert len(calls) == 2
