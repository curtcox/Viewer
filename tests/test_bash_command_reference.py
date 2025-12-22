"""Tests for bash command reference assets."""

from __future__ import annotations

import json
from pathlib import Path

from common_commands import COMMON_COMMANDS
from docs.bash_commands_builder import render_bash_commands_markdown


def _load_server_names(source_path: str) -> set[str]:
    data = json.loads(Path(source_path).read_text())
    return {server["name"] for server in data["servers"]}


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


def test_pipeline_example_present():
    """The shared three-command pipeline example should be visible in the docs."""

    doc_text = Path("docs/bash_commands.md").read_text()
    example_path = "/tr/a-z%20A-Z/rev/echo/hello"
    assert example_path in doc_text
    assert f"{example_path}?debug=true" in doc_text
