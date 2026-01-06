import itertools

from server_execution.conditional_execution import (
    execute_if,
    execute_try,
    parse_do_segments,
    parse_if_segments,
    parse_try_segments,
    run_do_loop,
)


def test_if_then_else(monkeypatch):
    responses = {
        tuple(["echo", "true"]): "true",
        tuple(["echo", "yes"]): "yes",
        tuple(["echo", "no"]): "no",
    }

    monkeypatch.setattr(
        "server_execution.conditional_execution._execute_path",
        lambda segments: responses.get(tuple(segments), ""),
    )

    parts = parse_if_segments(["echo", "true", "then", "echo", "yes", "else", "echo", "no"])
    output, status, headers = execute_if(parts)

    assert output == "yes"
    assert status == 200
    assert headers["Content-Type"] == "text/html"


def test_do_loop_and_cost_limit(monkeypatch):
    call_counter = itertools.count(1)

    def fake_execute(segments):
        if segments == ["echo", "x"]:
            return "x" * 600000
        if segments == ["echo", "false"]:
            return "false"
        if segments == ["echo", "true"]:
            # Ensure the loop sees at least one truthy condition
            return "true" if next(call_counter) == 1 else "false"
        return ""

    monkeypatch.setattr(
        "server_execution.conditional_execution._execute_path",
        fake_execute,
    )

    parts = parse_do_segments(["echo", "x", "while", "echo", "true"])
    output, status, headers = run_do_loop(parts)

    assert "X-Loop-Terminated" in headers
    assert headers["X-Loop-Terminated"] == "cost"
    assert output.startswith("x")
    assert status == 200


def test_try_catch_status(monkeypatch):
    from flask import Flask

    def fake_execute(segments):
        if segments == ["status", "404"]:
            return "", 404, {"Content-Type": "text/plain"}
        return "caught"

    monkeypatch.setattr(
        "server_execution.conditional_execution._execute_path",
        fake_execute,
    )

    app = Flask(__name__)
    with app.app_context():
        parts = parse_try_segments(["status", "404", "catch", "echo", "caught"])
        output, status, headers = execute_try(parts)

    assert output == "caught"
    assert status == 200
    assert headers.get("X-Error-Status") == "404"

