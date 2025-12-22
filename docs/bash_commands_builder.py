"""Generate the bash commands reference document from shared metadata."""

from __future__ import annotations

from textwrap import dedent

from common_commands import COMMON_COMMANDS, CommandInfo


def _example_links(path: str) -> str:
    return f"[Execute]({path}) · [Debug]({path}?debug=true)"


def _example_block(command: CommandInfo) -> list[str]:
    base_path = f"/{command.name}"
    parameter_path = f"{base_path}/--help"
    pipeline_path = f"{base_path}/_/echo/Hello%20World"

    return [
        f"- Just the command: {_example_links(base_path)}",
        f"- With parameters: {_example_links(parameter_path)}",
        f"- In a pipeline: {_example_links(pipeline_path)}",
    ]


def render_bash_commands_markdown(commands: list[CommandInfo]) -> str:
    """Render the docs/bash_commands.md content."""

    lines: list[str] = [
        "# Bash command servers",
        "",
        "This document lists all bash-based servers, their roles, and quick links to run them. ",
        "Use `_` as a placeholder argument when you want to chain input without passing options to the command.",
        "",
        "## At-a-glance roles",
        "",
        "| Command | Role | Description |",
        "| --- | --- | --- |",
    ]

    for command in commands:
        lines.append(
            f"| `{command.name}` | {command.role} | {command.description} |"
        )

    lines.extend(
        [
            "",
            "## Example 3-command pipeline",
            "",
            "Pipeline URLs execute from right to left. The example below uppercases text using three commands:",
            "",
            "- `echo` provides the input",
            "- `rev` reverses the string",
            "- `tr` translates lowercase to uppercase",
            "",
        ]
    )

    pipeline_path = "/tr/a-z%20A-Z/rev/_/echo/hello"
    lines.append(f"- Pipeline: {_example_links(pipeline_path)}")
    lines.append("")

    lines.append("## Command reference")
    lines.append("")

    for command in commands:
        lines.append(f"### `{command.name}` ({command.role})")
        lines.append("")
        lines.append(command.description)
        lines.append("")
        lines.extend(_example_block(command))
        lines.append("")

    return dedent("\n".join(lines)).strip() + "\n"
