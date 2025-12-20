#!/usr/bin/env python3
"""Generate Python code smells reports using PyExamine for CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Sequence


@dataclass
class SmellsConfig:
    """Configuration for Python smells analysis."""

    project_path: Path
    output_dir: Path


class SmellsError(RuntimeError):
    """Raised when the Python smells detector command fails."""


def _run_command(
    command: Sequence[str], cwd: Path | None = None
) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and exit code."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        raise SmellsError(
            "PyExamine (analyze_code_quality) is not installed. "
            "Install from https://github.com/KarthikShivasankar/python_smells_detector"
        ) from exc

    return result.stdout, result.stderr, result.returncode


def _parse_smells_output(output: str) -> dict[str, int]:
    """Parse the smells output to extract summary statistics."""
    stats = {
        "code_smells": 0,
        "architectural_smells": 0,
        "structural_smells": 0,
        "total": 0,
    }

    lines = output.split("\n")
    for line in lines:
        line_lower = line.lower()
        # Look for patterns in the output that indicate smell counts
        if "code smell" in line_lower and "found" in line_lower:
            try:
                # Extract number from patterns like "Found X code smells"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == "found" and i + 1 < len(parts):
                        stats["code_smells"] = int(parts[i + 1])
                        break
            except (ValueError, IndexError):
                pass
        elif "architectural smell" in line_lower and "found" in line_lower:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == "found" and i + 1 < len(parts):
                        stats["architectural_smells"] = int(parts[i + 1])
                        break
            except (ValueError, IndexError):
                pass
        elif "structural smell" in line_lower and "found" in line_lower:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == "found" and i + 1 < len(parts):
                        stats["structural_smells"] = int(parts[i + 1])
                        break
            except (ValueError, IndexError):
                pass

    stats["total"] = (
        stats["code_smells"]
        + stats["architectural_smells"]
        + stats["structural_smells"]
    )
    return stats


def _format_markdown_summary(stats: dict[str, int], output_text: str) -> str:
    """Format the smells findings as a Markdown summary."""
    lines = [
        "# Python Code Smells Analysis (PyExamine)",
        "",
    ]

    if stats["total"] == 0:
        lines.extend(
            [
                "No code smells detected! 🎉",
                "",
                "PyExamine analyzed the codebase for:",
                "- Code smells (e.g., long methods, large classes)",
                "- Architectural smells (e.g., cyclic dependencies)",
                "- Structural issues (e.g., high complexity)",
            ]
        )
    else:
        lines.extend(
            [
                f"* Found {stats['total']} total code smell(s)",
                f"* Code smells: {stats['code_smells']}",
                f"* Architectural smells: {stats['architectural_smells']}",
                f"* Structural smells: {stats['structural_smells']}",
                "",
                "## Summary",
                "",
                "| Category | Count |",
                "| --- | ---: |",
                f"| Code Smells | {stats['code_smells']} |",
                f"| Architectural Smells | {stats['architectural_smells']} |",
                f"| Structural Smells | {stats['structural_smells']} |",
                f"| **Total** | **{stats['total']}** |",
            ]
        )

    return "\n".join(lines) + "\n"


def _format_html_report(stats: dict[str, int], output_text: str) -> str:
    """Format the smells findings as an HTML report."""

    summary_text = (
        f"Found {stats['total']} code smell(s)."
        if stats["total"] > 0
        else "No code smells detected!"
    )

    # Escape the output text for HTML
    escaped_output = (
        escape(output_text) if output_text else "No detailed output available."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Python Code Smells Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    h1 {{ font-size: 2rem; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }}
    th {{ background: #f6f8fa; }}
    td.numeric {{ text-align: right; }}
    section {{ margin-top: 2rem; }}
    pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
    .summary {{ background: #f1f8ff; border-left: 4px solid #0969da; padding: 1rem; }}
  </style>
</head>
<body>
  <h1>Python Code Smells Report (PyExamine)</h1>
  <div class="summary">
    <p>{escape(summary_text)} PyExamine detects code smells, architectural issues,
    and structural problems in Python projects. This helps identify maintainability
    issues and technical debt early.</p>
  </div>
  <section>
    <h2>Summary by category</h2>
    <table>
      <thead>
        <tr><th>Category</th><th>Count</th></tr>
      </thead>
      <tbody>
        <tr><td>Code Smells</td><td class="numeric">{stats["code_smells"]}</td></tr>
        <tr><td>Architectural Smells</td><td class="numeric">{stats["architectural_smells"]}</td></tr>
        <tr><td>Structural Smells</td><td class="numeric">{stats["structural_smells"]}</td></tr>
        <tr><td><strong>Total</strong></td><td class="numeric"><strong>{stats["total"]}</strong></td></tr>
      </tbody>
    </table>
  </section>
  <section>
    <h2>Detailed output</h2>
    <pre>{escaped_output}</pre>
  </section>
</body>
</html>
"""


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(argv: Sequence[str] | None = None) -> int:
    """Run Python smells detector and generate reports."""
    parser = argparse.ArgumentParser(
        description="Run PyExamine python_smells_detector and publish reports."
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path("."),
        help="Path to the project to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the generated report files.",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        help="Where to write the Markdown summary.",
    )

    args = parser.parse_args(argv)

    project_path = args.project_path.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the smells detector
    # Note: analyze_code_quality may not be installed, so we handle that gracefully
    command = ["analyze_code_quality", str(project_path)]

    print(f"Running PyExamine on {project_path}...")
    output, stderr, exit_code = _run_command(command)

    # Check for command failure
    # PyExamine may exit non-zero when it finds smells or encounters errors
    # We need to distinguish between legitimate findings and actual failures
    if exit_code != 0:
        # Check if output looks like an error rather than findings
        combined_output = f"{output}\n{stderr}".lower()
        error_indicators = [
            "error:",
            "traceback",
            "exception:",
            "failed to",
            "could not",
            "no such file",
            "permission denied",
            "invalid",
            "cannot",
        ]

        # If we see error indicators and have very little/no output, it's likely a real error
        has_error_indicators = any(
            indicator in combined_output for indicator in error_indicators
        )
        has_minimal_output = len(output.strip()) < 50

        if has_error_indicators and has_minimal_output:
            error_msg = f"PyExamine command failed with exit code {exit_code}."
            if stderr.strip():
                error_msg = f"{error_msg}\nStderr: {stderr.strip()}"
            if output.strip():
                error_msg = f"{error_msg}\nStdout: {output.strip()}"
            raise SmellsError(error_msg)

    # Combine stdout and stderr for full output
    full_output = output
    if stderr:
        full_output += f"\n\nStderr:\n{stderr}"

    # Parse the output to extract statistics
    stats = _parse_smells_output(output)

    # Generate reports
    markdown = _format_markdown_summary(stats, output)
    html = _format_html_report(stats, full_output)

    _write_file(output_dir / "summary.md", markdown)
    _write_file(output_dir / "index.html", html)
    _write_file(output_dir / "smells-output.txt", full_output)

    if args.summary_file:
        _write_file(args.summary_file, markdown)

    print(markdown)

    # Note any issues found
    if stats["total"] > 0:
        print(
            f"::warning::PyExamine found {stats['total']} code smell(s). "
            f"Review the report for details.",
            file=sys.stderr,
        )

    # Don't fail the build for code smells - just report them
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
