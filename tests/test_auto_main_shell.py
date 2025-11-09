from pathlib import Path
from types import SimpleNamespace

import pytest

import server_execution
from app import app
from server_templates.definitions import auto_main_shell
from text_function_runner import run_text_function


@pytest.fixture
def patched_server_execution(monkeypatch):
    """Provide a predictable environment for server execution tests."""
    from server_execution import code_execution

    monkeypatch.setattr(
        code_execution,
        "current_user",
        SimpleNamespace(id="user-123"),
    )
    monkeypatch.setattr(
        code_execution,
        "_load_user_context",
        lambda: {"variables": {}, "secrets": {}, "servers": {}},
    )

    def fake_success(output, content_type, server_name):
        return {
            "output": output,
            "content_type": content_type,
            "server_name": server_name,
        }

    monkeypatch.setattr(code_execution, "_handle_successful_execution", fake_success)


def test_auto_main_shell_main_executes_shell_command():
    result = auto_main_shell.main(command="echo direct-shell-test")

    assert result["content_type"] == "text/html"
    assert "<pre>" in result["output"]
    assert "$ echo direct-shell-test" in result["output"]
    assert "direct-shell-test" in result["output"]
    assert "[exit 0]" in result["output"]


def test_auto_main_shell_runs_through_text_function_runner():
    definition = """
from server_templates.definitions import auto_main_shell

return auto_main_shell.main(command=command)
""".strip()

    result = run_text_function(definition, {"command": "echo text-runner"})

    assert result["content_type"] == "text/html"
    assert "$ echo text-runner" in result["output"]
    assert "text-runner" in result["output"]
    assert "[exit 0]" in result["output"]


def test_auto_main_shell_executes_via_server_execution(patched_server_execution):
    definition = Path("server_templates/definitions/auto_main_shell.py").read_text(encoding='utf-8')

    with app.test_request_context("/shell", json={"command": "echo server-execution"}):
        result = server_execution.execute_server_code_from_definition(
            definition, "shell-runner"
        )

    assert result["server_name"] == "shell-runner"
    assert result["content_type"] == "text/html"
    assert "$ echo server-execution" in result["output"]
    assert "server-execution" in result["output"]
    assert "[exit 0]" in result["output"]
