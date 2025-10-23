# ruff: noqa: F821, F706
"""Automatic main() mapping template for executing shell commands."""

from __future__ import annotations

import os
import subprocess
from html import escape


def _gather_command_output(result: subprocess.CompletedProcess[str]) -> str:
    """Combine stdout and stderr into a single display string."""

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    segments: list[str] = []
    if stdout:
        segments.append(stdout.rstrip("\n"))
    if stderr:
        segments.append(stderr.rstrip("\n"))

    combined = "\n".join(segments)
    exit_line = f"[exit {result.returncode}]"

    if combined:
        return f"{combined}\n{exit_line}"
    return exit_line


def main(
    command: str = "",
    endpoint: str | None = None,
    context=None,
):
    """Render a minimal HTML shell runner and execute submitted commands."""

    shell_endpoint = endpoint or os.environ.get("SHELL_ENDPOINT", "/shell")
    command_text = command.strip() if isinstance(command, str) else ""

    executed = None
    command_result = None
    if command_text:
        executed = command_text
        completed = subprocess.run(  # noqa: S602
            command_text,
            shell=True,
            capture_output=True,
            text=True,
        )
        gathered = _gather_command_output(completed)
        command_result = f"$ {executed}\n{gathered}" if gathered else f"$ {executed}"

    parts = [
        "<!DOCTYPE html>",
        "<html><body>",
        f"<form method=\"post\" action=\"{escape(shell_endpoint, quote=True)}\">",
        "<input type=\"text\" name=\"command\" autofocus>",
        "<button type=\"submit\">Run</button>",
        "</form>",
    ]

    if executed is not None:
        parts.append("<pre>")
        parts.append(escape(command_result or "", quote=False))
        parts.append("</pre>")

    parts.append("</body></html>")

    return {
        "output": "".join(parts),
        "content_type": "text/html",
    }
