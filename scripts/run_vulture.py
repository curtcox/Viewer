#!/usr/bin/env python3
"""Generate Vulture dead code reports for CI."""

from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Sequence

import tomllib


@dataclass
class DeadCodeEntry:
    """Represents a single dead code finding from Vulture."""

    path: str
    line: int
    confidence: int
    message: str
    item_type: str


@dataclass
class VultureConfig:
    """Configuration for Vulture analysis."""

    paths: list[str]
    exclude: list[str]
    min_confidence: int
    ignore_decorators: list[str]
    ignore_names: list[str]
    make_whitelist: bool


class VultureError(RuntimeError):
    """Raised when the Vulture command fails."""


def _load_config(path: Path) -> dict[str, object]:
    """Load Vulture configuration from pyproject.toml."""
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        raise VultureError(f"Unable to read configuration file: {path}") from exc

    data = tomllib.loads(content)
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return {}

    vulture_data = tool.get("vulture")
    if isinstance(vulture_data, dict):
        return vulture_data
    return {}


def _resolve_config(raw: dict[str, object], args: argparse.Namespace) -> VultureConfig:
    """Resolve Vulture configuration from file and CLI arguments."""

    def _as_list(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            items: list[str] = []
            for entry in value:
                if isinstance(entry, str):
                    items.append(entry)
            return items
        return []

    paths = list(args.paths) if args.paths else _as_list(raw.get("paths")) or ["."]
    exclude = (
        list(args.exclude) if args.exclude is not None else _as_list(raw.get("exclude"))
    )

    min_confidence = (
        args.min_confidence
        if args.min_confidence is not None
        else raw.get("min_confidence", 80)
    )
    if not isinstance(min_confidence, int):
        min_confidence = 80
    min_confidence = max(0, min(100, min_confidence))

    ignore_decorators = _as_list(raw.get("ignore_decorators"))
    ignore_names = _as_list(raw.get("ignore_names"))
    make_whitelist = bool(raw.get("make_whitelist", False))

    return VultureConfig(
        paths=paths,
        exclude=exclude,
        min_confidence=min_confidence,
        ignore_decorators=ignore_decorators,
        ignore_names=ignore_names,
        make_whitelist=make_whitelist,
    )


def _build_vulture_command(
    *,
    exclude: Sequence[str],
    ignore_decorators: Sequence[str],
    ignore_names: Sequence[str],
    min_confidence: int,
    paths: Sequence[str],
    make_whitelist: bool = False,
) -> list[str]:
    """Build the Vulture command with all options."""
    command = ["vulture"]

    if exclude:
        for pattern in exclude:
            command.extend(["--exclude", pattern])

    if ignore_decorators:
        for decorator in ignore_decorators:
            command.extend(["--ignore-decorators", decorator])

    if ignore_names:
        for name in ignore_names:
            command.extend(["--ignore-names", name])

    command.extend(["--min-confidence", str(min_confidence)])

    if make_whitelist:
        command.append("--make-whitelist")

    command.extend(paths)
    return command


def _run_command(command: Sequence[str]) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and exit code."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        raise VultureError(
            "Vulture is not installed. Run 'pip install vulture' to install it."
        ) from exc

    return result.stdout, result.stderr, result.returncode


def _parse_vulture_output(output: str) -> list[DeadCodeEntry]:
    """Parse Vulture CSV output into structured entries."""
    entries: list[DeadCodeEntry] = []

    if not output.strip():
        return entries

    reader = csv.DictReader(io.StringIO(output))

    for row in reader:
        try:
            # Vulture CSV format: filename,line_number,confidence,message,item_type
            entry = DeadCodeEntry(
                path=row.get("filename", ""),
                line=int(row.get("line_number", 0)),
                confidence=int(row.get("confidence", 0)),
                message=row.get("message", ""),
                item_type=row.get("item_type", "unknown"),
            )
            entries.append(entry)
        except (ValueError, KeyError):
            continue

    return entries


def _categorize_entries(
    entries: Sequence[DeadCodeEntry],
) -> dict[str, list[DeadCodeEntry]]:
    """Categorize dead code entries by type."""
    categories: dict[str, list[DeadCodeEntry]] = {}

    for entry in entries:
        category = entry.item_type or "unknown"
        if category not in categories:
            categories[category] = []
        categories[category].append(entry)

    return categories


def _format_markdown_summary(
    entries: Sequence[DeadCodeEntry],
    config: VultureConfig,
) -> str:
    """Format Vulture findings as a Markdown summary."""
    lines = [
        "# Vulture dead code analysis",
        "",
    ]

    if not entries:
        lines.extend(
            [
                "No dead code detected! 🎉",
                "",
                f"Vulture scanned with minimum confidence level: {config.min_confidence}%",
            ]
        )
        return "\n".join(lines) + "\n"

    categories = _categorize_entries(entries)
    unique_files = len({entry.path for entry in entries})

    lines.extend(
        [
            f"* Found {len(entries)} potential dead code issue(s) across {unique_files} file(s).",
            f"* Minimum confidence threshold: {config.min_confidence}%",
            "",
            "## Summary by type",
            "",
            "| Type | Count |",
            "| --- | ---: |",
        ]
    )

    for item_type in sorted(categories.keys()):
        count = len(categories[item_type])
        lines.append(f"| {item_type} | {count} |")

    lines.extend(
        [
            "",
            "## Dead code findings",
            "",
            "| File | Line | Confidence | Type | Message |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )

    for entry in sorted(entries, key=lambda e: (e.path, e.line)):
        lines.append(
            f"| {entry.path} | {entry.line} | {entry.confidence}% | {entry.item_type} | {entry.message} |"
        )

    if config.exclude:
        lines.extend(["", "## Excluded patterns", ""])
        for pattern in config.exclude:
            lines.append(f"- {pattern}")

    if config.ignore_names:
        lines.extend(["", "## Ignored names", ""])
        for name in config.ignore_names:
            lines.append(f"- {name}")

    if config.ignore_decorators:
        lines.extend(["", "## Ignored decorators", ""])
        for decorator in config.ignore_decorators:
            lines.append(f"- {decorator}")

    return "\n".join(lines) + "\n"


def _format_html_report(
    entries: Sequence[DeadCodeEntry],
    config: VultureConfig,
) -> str:
    """Format Vulture findings as an HTML report."""

    def _render_rows() -> str:
        if not entries:
            return '      <tr><td colspan="5">No dead code detected! 🎉</td></tr>'

        rows: list[str] = []
        for entry in sorted(entries, key=lambda e: (e.path, e.line)):
            rows.append(
                f"      <tr><td>{escape(entry.path)}</td>"
                f'<td class="numeric">{entry.line}</td>'
                f'<td class="numeric">{entry.confidence}%</td>'
                f"<td>{escape(entry.item_type)}</td>"
                f"<td>{escape(entry.message)}</td></tr>"
            )
        return "\n".join(rows)

    def _render_list(title: str, items: Sequence[str]) -> str:
        if not items:
            return ""
        lis = "\n".join(f"      <li>{escape(item)}</li>" for item in items)
        return f"    <section><h2>{escape(title)}</h2><ul>\n{lis}\n    </ul></section>"

    categories = _categorize_entries(entries)
    unique_files = len({entry.path for entry in entries})

    summary_text = (
        f"Found {len(entries)} potential dead code issue(s) across {unique_files} file(s)."
        if entries
        else "No dead code detected!"
    )

    categories_rows = ""
    if categories:
        cat_rows = []
        for item_type in sorted(categories.keys()):
            count = len(categories[item_type])
            cat_rows.append(
                f'      <tr><td>{escape(item_type)}</td><td class="numeric">{count}</td></tr>'
            )
        categories_rows = f"""
  <section>
    <h2>Summary by type</h2>
    <table>
      <thead>
        <tr><th>Type</th><th>Count</th></tr>
      </thead>
      <tbody>
{chr(10).join(cat_rows)}
      </tbody>
    </table>
  </section>"""

    exclusions_section = _render_list("Excluded patterns", config.exclude)
    ignore_names_section = _render_list("Ignored names", config.ignore_names)
    ignore_decorators_section = _render_list(
        "Ignored decorators", config.ignore_decorators
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Vulture dead code report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    h1 {{ font-size: 2rem; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }}
    th {{ background: #f6f8fa; }}
    td.numeric {{ text-align: right; }}
    section {{ margin-top: 2rem; }}
    ul {{ list-style: disc; padding-left: 1.5rem; }}
    .summary {{ background: #f1f8ff; border-left: 4px solid #0969da; padding: 1rem; }}
  </style>
</head>
<body>
  <h1>Vulture dead code report</h1>
  <div class="summary">
    <p>{escape(summary_text)} Vulture analyzes Python code to find unused
    functions, classes, variables, attributes, properties, imports, and more.
    Results with confidence levels below {config.min_confidence}% are filtered out.</p>
  </div>{categories_rows}
  <section>
    <h2>Dead code findings</h2>
    <table>
      <thead>
        <tr><th>File</th><th>Line</th><th>Confidence</th><th>Type</th><th>Message</th></tr>
      </thead>
      <tbody>
{_render_rows()}
      </tbody>
    </table>
  </section>
{exclusions_section}
{ignore_names_section}
{ignore_decorators_section}
</body>
</html>
"""


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(argv: Sequence[str] | None = None) -> int:
    """Run Vulture and generate reports."""
    parser = argparse.ArgumentParser(
        description="Run Vulture and publish dead code reports."
    )
    parser.add_argument(
        "paths", nargs="*", help="Paths to analyse. Defaults to configured paths."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to the Vulture configuration file.",
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
    parser.add_argument(
        "--exclude",
        nargs="*",
        help="Override the configured exclusion patterns.",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        help="Override the minimum confidence threshold (0-100).",
    )

    args = parser.parse_args(argv)

    raw_config = _load_config(args.config)
    config = _resolve_config(raw_config, args)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # First, get CSV output for parsing
    csv_command = _build_vulture_command(
        exclude=config.exclude,
        ignore_decorators=config.ignore_decorators,
        ignore_names=config.ignore_names,
        min_confidence=config.min_confidence,
        paths=config.paths,
    )
    csv_command.append("--sort-by-size")

    # Vulture doesn't have a built-in CSV format, so we'll parse the regular output
    output, stderr, exit_code = _run_command(csv_command)

    # Vulture exit codes:
    # 0 = no dead code found (success)
    # 1 = file/path errors (e.g., file not found, parse errors)
    # 2 = invalid arguments/options
    # 3+ = dead code found (varies based on findings)
    #
    # We need to distinguish between "dead code found" (legitimate, don't fail)
    # and "vulture invocation error" (illegitimate, should fail).

    # Exit code 2 is always invalid arguments
    if exit_code == 2:
        error_msg = (
            f"Vulture command failed with invalid arguments (exit code {exit_code})."
        )
        if stderr.strip():
            error_msg = f"{error_msg}\nStderr: {stderr.strip()}"
        if output.strip():
            error_msg = f"{error_msg}\nStdout: {output.strip()}"
        raise VultureError(error_msg)

    # For other non-zero exit codes, check if the output looks like an error
    if exit_code != 0:
        combined_output = f"{output}\n{stderr}".lower()
        error_indicators = [
            "error:",
            "could not be found",
            "no such file",
            "permission denied",
            "failed to",
            "unexpected character",
        ]

        if any(indicator in combined_output for indicator in error_indicators):
            error_msg = f"Vulture command failed with exit code {exit_code}."
            if stderr.strip():
                error_msg = f"{error_msg}\nStderr: {stderr.strip()}"
            if output.strip():
                error_msg = f"{error_msg}\nStdout: {output.strip()}"
            raise VultureError(error_msg)

    # Parse the vulture output (format: path:line: message (confidence%))
    entries = _parse_vulture_text_output(output)

    # Generate reports
    markdown = _format_markdown_summary(entries, config)
    html = _format_html_report(entries, config)

    _write_file(output_dir / "summary.md", markdown)
    _write_file(output_dir / "index.html", html)
    _write_file(output_dir / "vulture-output.txt", output)

    if args.summary_file:
        _write_file(args.summary_file, markdown)

    print(markdown)

    # Vulture exits with 0 if no dead code found, non-zero otherwise
    # We don't want to fail the build for dead code, just report it
    if entries:
        print(
            f"::warning::Vulture found {len(entries)} potential dead code issue(s). "
            f"Review the report for details.",
            file=sys.stderr,
        )

    return 0


def _parse_vulture_text_output(output: str) -> list[DeadCodeEntry]:
    """Parse Vulture text output into structured entries."""
    entries: list[DeadCodeEntry] = []

    if not output.strip():
        return entries

    for line in output.strip().split("\n"):
        # Vulture output format: path:line: message (confidence%)
        # Example: app.py:42: unused function 'foo' (60% confidence)
        if not line.strip():
            continue

        try:
            # Split on first two colons to get path, line, and rest
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue

            path = parts[0].strip()
            line_num = int(parts[1].strip())
            rest = parts[2].strip()

            # Extract confidence from the end (XX% confidence)
            confidence = 80  # default
            message = rest
            item_type = "unknown"

            if "(" in rest and "% confidence)" in rest:
                message_part, conf_part = rest.rsplit("(", 1)
                message = message_part.strip()
                conf_str = conf_part.replace("% confidence)", "").strip()
                try:
                    confidence = int(conf_str)
                except ValueError:
                    pass

            # Determine item type from message
            if "unused function" in message.lower():
                item_type = "function"
            elif "unused method" in message.lower():
                item_type = "method"
            elif "unused class" in message.lower():
                item_type = "class"
            elif "unused variable" in message.lower():
                item_type = "variable"
            elif "unused attribute" in message.lower():
                item_type = "attribute"
            elif "unused import" in message.lower():
                item_type = "import"
            elif "unused property" in message.lower():
                item_type = "property"

            entry = DeadCodeEntry(
                path=path,
                line=line_num,
                confidence=confidence,
                message=message,
                item_type=item_type,
            )
            entries.append(entry)
        except (ValueError, IndexError):
            continue

    return entries


if __name__ == "__main__":
    raise SystemExit(run())
