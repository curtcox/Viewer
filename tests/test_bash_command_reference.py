"""Tests for bash command reference assets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common_commands import COMMON_COMMANDS
from docs.bash_commands_builder import render_bash_commands_markdown

EXAMPLE_PARAM = "--help"
EXAMPLE_PIPE_INPUT = "Hello World"
THREE_COMMAND_PIPE_INPUT = "hello"
DEFINITIONS_DIR = Path("reference_templates/servers/definitions")


def _load_server_names(source_path: str) -> set[str]:
    data = json.loads(Path(source_path).read_text())
    return {server["name"] for server in data["servers"]}


def _build_args_from_path(arg_text: str | None) -> list[str]:
    """Replicate the server script's path argument parsing."""

    if not arg_text or arg_text == "_":
        return []
    return arg_text.split()


def _simulate_stub_output(command_name: str, args: list[str], stdin_value: str) -> str:
    """Simulate the output produced by the stubbed command template."""

    args_text = "<none>" if not args else " ".join(args)
    stdin_text = "<none>" if stdin_value == "" else stdin_value
    return f"cmd={command_name}\nargs={args_text}\nstdin={stdin_text}\n"


def test_bash_commands_doc_is_generated():
    """docs/bash_commands.md should match the generator output."""

    expected = render_bash_commands_markdown(COMMON_COMMANDS)
    actual = Path("docs/bash_commands.md").read_text()

    assert actual == expected


def test_all_bash_command_definitions_exist():
    """Every command should have a generated bash server definition."""

    for command in COMMON_COMMANDS:
        path = Path(f"reference_templates/servers/definitions/{command.name}.sh")
        assert path.exists(), f"Missing definition for {command.name}"

        text = path.read_text()
        assert f'COMMAND="{command.name}"' in text
        assert "BASH_COMMAND_STUB_DIR" in text
        assert "use '_' to skip while piping" in text


def test_boot_images_include_expected_commands():
    """Default boot should have all commands and readonly should exclude duals."""

    default_names = _load_server_names("reference_templates/default.boot.source.json")
    readonly_names = _load_server_names("reference_templates/readonly.boot.source.json")

    command_names = {command.name for command in COMMON_COMMANDS}
    safe_names = {command.name for command in COMMON_COMMANDS if command.safe_for_readonly}
    dual_names = command_names - safe_names

    assert command_names.issubset(default_names)
    assert safe_names.issubset(readonly_names)
    assert readonly_names.isdisjoint(dual_names)


@pytest.mark.parametrize(
    ("arg_text", "stdin_value"),
    [
        (None, ""),
        (EXAMPLE_PARAM, ""),
        ("_", EXAMPLE_PIPE_INPUT),
    ],
)
@pytest.mark.parametrize("command_name", [command.name for command in COMMON_COMMANDS])
def test_doc_examples_match_direct_bash(command_name: str, arg_text: str | None, stdin_value: str):
    """Each documented example should behave like the direct bash invocation."""

    if arg_text == "_":
        echo_args = _build_args_from_path(EXAMPLE_PIPE_INPUT)
        stdin_value = _simulate_stub_output("echo", echo_args, "")

    server_args = _build_args_from_path(arg_text)
    server_stdout = _simulate_stub_output(command_name, server_args, stdin_value)

    direct_arg_text = "" if arg_text in (None, "_") else arg_text
    direct_args = _build_args_from_path(direct_arg_text)
    direct_stdin = stdin_value if arg_text == "_" else ""
    direct_stdout = _simulate_stub_output(command_name, direct_args, direct_stdin)

    assert server_stdout == direct_stdout


def test_three_command_pipeline_matches_bash():
    """The 3-command pipeline example should align with running the commands directly."""

    echo_output = _simulate_stub_output("echo", _build_args_from_path(THREE_COMMAND_PIPE_INPUT), "")
    rev_output = _simulate_stub_output("rev", [], echo_output)
    tr_output = _simulate_stub_output("tr", ["a-z", "A-Z"], rev_output)

    direct_echo_output = _simulate_stub_output(
        "echo", _build_args_from_path(THREE_COMMAND_PIPE_INPUT), ""
    )
    direct_rev_output = _simulate_stub_output("rev", [], direct_echo_output)
    direct_tr_output = _simulate_stub_output("tr", ["a-z", "A-Z"], direct_rev_output)

    assert tr_output == direct_tr_output


def test_pipeline_example_present():
    """The shared three-command pipeline example should be visible in the docs."""

    doc_text = Path("docs/bash_commands.md").read_text()
    example_path = "/tr/a-z%20A-Z/rev/_/echo/hello"
    assert example_path in doc_text
    assert f"{example_path}?debug=true" in doc_text
