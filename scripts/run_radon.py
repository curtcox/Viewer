#!/usr/bin/env python3
"""Generate Radon complexity and maintainability reports for CI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable, Sequence

import tomllib

RANK_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
MI_THRESHOLDS = (
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (25, "E"),
)


@dataclass
class ComplexityEntry:
    path: str
    block_type: str
    name: str
    lineno: int
    complexity: float
    rank: str


@dataclass
class MaintainabilityEntry:
    path: str
    mi: float
    rank: str


@dataclass
class RadonConfig:
    paths: list[str]
    exclude: list[str]
    ignore: list[str]
    fail_rank: str
    top_results: int


class RadonError(RuntimeError):
    """Raised when the Radon command fails."""


def _load_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem errors should fail fast
        raise RadonError(f"Unable to read configuration file: {path}") from exc

    data = tomllib.loads(content)
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return {}

    radon_data = tool.get("radon")
    if isinstance(radon_data, dict):
        return radon_data
    return {}


def _resolve_config(raw: dict[str, object], args: argparse.Namespace) -> RadonConfig:
    def _as_list(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, Iterable):
            items: list[str] = []
            for entry in value:
                if isinstance(entry, str):
                    items.append(entry)
            return items
        return []

    paths = list(args.paths) if args.paths else _as_list(raw.get("paths")) or ["."]
    exclude = (
        list(args.exclude)
        if args.exclude is not None
        else _as_list(raw.get("exclude"))
    )
    ignore = (
        list(args.ignore)
        if args.ignore is not None
        else _as_list(raw.get("ignore"))
    )

    fail_rank = (args.fail_rank or raw.get("fail_rank") or "E").upper()
    if fail_rank not in RANK_ORDER:
        valid = ", ".join(RANK_ORDER)
        raise RadonError(f"Invalid fail rank '{fail_rank}'. Choose one of: {valid}.")

    top_results = args.top if args.top is not None else raw.get("report_top", 20)
    if not isinstance(top_results, int) or top_results <= 0:
        top_results = 20

    return RadonConfig(
        paths=paths,
        exclude=exclude,
        ignore=ignore,
        fail_rank=fail_rank,
        top_results=top_results,
    )


def _build_radon_command(
    base: Sequence[str],
    *,
    exclude: Sequence[str],
    ignore: Sequence[str],
    paths: Sequence[str],
) -> list[str]:
    command = list(base)
    if exclude:
        command.extend(["--exclude", ",".join(exclude)])
    if ignore:
        command.extend(["--ignore", ",".join(ignore)])
    command.extend(paths)
    return command


def _run_command(command: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - radon missing in CI
        raise RadonError(
            "Radon is not installed. Ensure the dependency is available in CI."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        message = f"Command {' '.join(command)} failed with exit code {result.returncode}."
        if stderr:
            message = f"{message}\n{stderr}"
        raise RadonError(message)

    return result.stdout


def _parse_complexity(data: str) -> tuple[list[ComplexityEntry], dict[str, object]]:
    payload = json.loads(data or "{}")
    entries: list[ComplexityEntry] = []
    extras: dict[str, object] = {}

    for path, blocks in payload.items():
        if isinstance(blocks, dict) and path == "average":
            extras[path] = blocks
            continue
        if isinstance(blocks, dict):
            extras[path] = blocks
            continue
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            try:
                entry = ComplexityEntry(
                    path=path,
                    block_type=str(block.get("type", "")),
                    name=str(block.get("name", "")),
                    lineno=int(block.get("lineno", 0)),
                    complexity=float(block.get("complexity", 0.0)),
                    rank=str(block.get("rank", "")).upper() or "?",
                )
            except (TypeError, ValueError):
                continue
            entries.append(entry)
    return entries, extras


def _mi_rank(value: float, declared: str | None) -> str:
    if declared and declared.upper() in RANK_ORDER:
        return declared.upper()
    for threshold, rank in MI_THRESHOLDS:
        if value >= threshold:
            return rank
    return "F"


def _parse_mi(data: str) -> tuple[list[MaintainabilityEntry], dict[str, object]]:
    payload = json.loads(data or "{}")
    entries: list[MaintainabilityEntry] = []
    extras: dict[str, object] = {}

    for path, info in payload.items():
        if path == "average":
            extras[path] = info
            continue
        rank: str | None = None
        value: float | None = None
        if isinstance(info, dict):
            maybe_value = info.get("mi")
            if isinstance(maybe_value, (int, float)):
                value = float(maybe_value)
            maybe_rank = info.get("rank")
            if isinstance(maybe_rank, str):
                rank = maybe_rank
        elif isinstance(info, (int, float)):
            value = float(info)
        if value is None:
            continue
        entries.append(
            MaintainabilityEntry(path=path, mi=value, rank=_mi_rank(value, rank))
        )
    return entries, extras


def _summarise_complexity(entries: Sequence[ComplexityEntry]) -> dict[str, int]:
    summary: dict[str, int] = {key: 0 for key in RANK_ORDER}
    for entry in entries:
        key = entry.rank if entry.rank in summary else "?"
        summary[key] = summary.get(key, 0) + 1
    return summary


def _summarise_mi(entries: Sequence[MaintainabilityEntry]) -> dict[str, int]:
    summary: dict[str, int] = {key: 0 for key in RANK_ORDER}
    for entry in entries:
        key = entry.rank if entry.rank in summary else "?"
        summary[key] = summary.get(key, 0) + 1
    return summary


def _format_markdown_summary(
    *,
    complexity: Sequence[ComplexityEntry],
    maintainability: Sequence[MaintainabilityEntry],
    config: RadonConfig,
    extras: dict[str, dict[str, object]],
) -> str:
    worst_complexity = max(
        (entry.rank for entry in complexity if entry.rank in RANK_ORDER),
        default="N/A",
        key=lambda rank: RANK_ORDER[rank],
    )
    worst_mi_entry = min(
        maintainability,
        default=None,
        key=lambda entry: entry.mi,
    )
    worst_mi_text = "N/A"
    if worst_mi_entry is not None:
        worst_mi_text = f"{worst_mi_entry.mi:.2f} ({worst_mi_entry.rank})"

    complexity_counts = _summarise_complexity(complexity)
    mi_counts = _summarise_mi(maintainability)

    unique_files = len({entry.path for entry in complexity})

    lines = [
        "# Radon summary",
        "",
        f"* Analysed {len(complexity)} code blocks across {unique_files} files.",
        f"* Worst cyclomatic complexity rank: {worst_complexity} (fails if worse than {config.fail_rank}).",
        f"* Lowest maintainability index: {worst_mi_text}.",
        "",
        "## Cyclomatic complexity distribution",
        "",
        "| Rank | Blocks |",
        "| --- | ---: |",
    ]

    for rank in RANK_ORDER:
        lines.append(f"| {rank} | {complexity_counts.get(rank, 0)} |")

    lines.extend(
        [
            "",
            "## Maintainability index distribution",
            "",
            "| Rank | Files |",
            "| --- | ---: |",
        ]
    )

    for rank in RANK_ORDER:
        lines.append(f"| {rank} | {mi_counts.get(rank, 0)} |")

    if complexity:
        lines.extend(["", "## Most complex code blocks", "", "| Rank | Complexity | Location | Block |", "| --- | ---: | --- | --- |"])
        for entry in sorted(
            complexity,
            key=lambda e: (RANK_ORDER.get(e.rank, 0), -e.complexity),
            reverse=True,
        )[: config.top_results]:
            location = f"{entry.path}:{entry.lineno}" if entry.lineno else entry.path
            block_name = entry.name or entry.block_type or "(anonymous)"
            lines.append(
                f"| {entry.rank} | {entry.complexity:.2f} | {location} | {block_name} |"
            )

    if maintainability:
        lines.extend(
            [
                "",
                "## Lowest maintainability files",
                "",
                "| Rank | MI | File |",
                "| --- | ---: | --- |",
            ]
        )
        for entry in sorted(maintainability, key=lambda e: e.mi)[: config.top_results]:
            lines.append(f"| {entry.rank} | {entry.mi:.2f} | {entry.path} |")

    if extras:
        lines.extend(["", "## Additional data", ""])
        for key, value in extras.items():
            lines.append(f"- **{key}**: `{json.dumps(value, sort_keys=True)}`")

    if config.exclude:
        lines.extend(["", "## Exclusions", ""])
        for pattern in config.exclude:
            lines.append(f"- {pattern}")

    if config.ignore:
        lines.extend(["", "## Ignored patterns", ""])
        for pattern in config.ignore:
            lines.append(f"- {pattern}")

    return "\n".join(lines) + "\n"


def _format_html_report(
    *,
    complexity: Sequence[ComplexityEntry],
    maintainability: Sequence[MaintainabilityEntry],
    config: RadonConfig,
    extras: dict[str, dict[str, object]],
) -> str:
    def _render_complexity_rows() -> str:
        rows: list[str] = []
        for entry in sorted(
            complexity,
            key=lambda e: (RANK_ORDER.get(e.rank, 0), -e.complexity),
            reverse=True,
        )[: config.top_results]:
            location = f"{escape(entry.path)}:{entry.lineno}" if entry.lineno else escape(entry.path)
            name = escape(entry.name or entry.block_type or "(anonymous)")
            rows.append(
                f"      <tr><td>{escape(entry.rank)}</td><td class=\"numeric\">{entry.complexity:.2f}</td><td>{location}</td><td>{name}</td></tr>"
            )
        return "\n".join(rows) or "      <tr><td colspan=\"4\">No code blocks matched the report criteria.</td></tr>"

    def _render_mi_rows() -> str:
        rows: list[str] = []
        for entry in sorted(maintainability, key=lambda e: e.mi)[: config.top_results]:
            rows.append(
                f"      <tr><td>{escape(entry.rank)}</td><td class=\"numeric\">{entry.mi:.2f}</td><td>{escape(entry.path)}</td></tr>"
            )
        return "\n".join(rows) or "      <tr><td colspan=\"3\">No files were analysed.</td></tr>"

    def _render_list(title: str, items: Sequence[str]) -> str:
        if not items:
            return ""
        lis = "\n".join(f"      <li>{escape(item)}</li>" for item in items)
        return f"    <section><h2>{escape(title)}</h2><ul>\n{lis}\n    </ul></section>"

    extras_section = ""
    if extras:
        items = [f"{key}: {json.dumps(value, sort_keys=True)}" for key, value in extras.items()]
        extras_section = _render_list("Additional data", items)

    exclusions_section = _render_list("Excluded paths", config.exclude)
    ignore_section = _render_list("Ignored file patterns", config.ignore)

    return """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Radon complexity report</title>
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
  <h1>Radon complexity report</h1>
  <div class=\"summary\">
    <p>This report summarises the cyclomatic complexity and maintainability index
    metrics gathered by <code>radon</code>. Blocks graded worse than
    <strong>{fail_rank}</strong> will fail the CI job. The tables below list the
    most complex blocks and files with the lowest maintainability scores. Only
    the top {top} results are shown to keep the report concise.</p>
  </div>
  <section>
    <h2>Most complex code blocks</h2>
    <table>
      <thead>
        <tr><th>Rank</th><th>Complexity</th><th>Location</th><th>Block</th></tr>
      </thead>
      <tbody>
{complexity_rows}
      </tbody>
    </table>
  </section>
  <section>
    <h2>Lowest maintainability files</h2>
    <table>
      <thead>
        <tr><th>Rank</th><th>Maintainability index</th><th>File</th></tr>
      </thead>
      <tbody>
{mi_rows}
      </tbody>
    </table>
  </section>
{extras_section}
{exclusions_section}
{ignore_section}
</body>
</html>
""".format(
        fail_rank=escape(config.fail_rank),
        top=config.top_results,
        complexity_rows=_render_complexity_rows(),
        mi_rows=_render_mi_rows(),
        extras_section=extras_section,
        exclusions_section=exclusions_section,
        ignore_section=ignore_section,
    )


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Radon and publish reports.")
    parser.add_argument("paths", nargs="*", help="Paths to analyse. Defaults to the configured paths.")
    parser.add_argument("--config", type=Path, default=Path("pyproject.toml"), help="Path to the Radon configuration file.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for the generated report files.")
    parser.add_argument("--summary-file", type=Path, help="Where to write the Markdown summary.")
    parser.add_argument("--exclude", nargs="*", help="Override the configured exclusion patterns.")
    parser.add_argument("--ignore", nargs="*", help="Override the configured ignore patterns.")
    parser.add_argument("--fail-rank", help="Override the fail threshold for cyclomatic complexity.")
    parser.add_argument("--top", type=int, help="Override the number of entries shown in summary tables.")

    args = parser.parse_args(argv)

    raw_config = _load_config(args.config)
    config = _resolve_config(raw_config, args)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_cc = ["radon", "cc", "--json", "--average", "--show-complexity", "--no-assert"]
    base_mi = ["radon", "mi", "--json", "--show"]

    cc_command = _build_radon_command(
        base_cc,
        exclude=config.exclude,
        ignore=config.ignore,
        paths=config.paths,
    )
    mi_command = _build_radon_command(
        base_mi,
        exclude=config.exclude,
        ignore=config.ignore,
        paths=config.paths,
    )

    cc_output = _run_command(cc_command)
    mi_output = _run_command(mi_command)

    complexity_entries, cc_extras = _parse_complexity(cc_output)
    mi_entries, mi_extras = _parse_mi(mi_output)

    extras: dict[str, dict[str, object]] = {}
    if cc_extras:
        extras.update({f"complexity_{key}": value for key, value in cc_extras.items()})
    if mi_extras:
        extras.update({f"maintainability_{key}": value for key, value in mi_extras.items()})

    markdown = _format_markdown_summary(
        complexity=complexity_entries,
        maintainability=mi_entries,
        config=config,
        extras=extras,
    )
    html = _format_html_report(
        complexity=complexity_entries,
        maintainability=mi_entries,
        config=config,
        extras=extras,
    )

    _write_file(output_dir / "complexity.json", json.dumps(json.loads(cc_output or "{}"), indent=2, sort_keys=True))
    _write_file(output_dir / "maintainability.json", json.dumps(json.loads(mi_output or "{}"), indent=2, sort_keys=True))
    _write_file(output_dir / "summary.md", markdown)
    _write_file(output_dir / "index.html", html)

    if args.summary_file:
        _write_file(args.summary_file, markdown)

    print(markdown)

    fail_rank = config.fail_rank
    threshold_index = RANK_ORDER[fail_rank]
    failures = [
        entry
        for entry in complexity_entries
        if entry.rank in RANK_ORDER and RANK_ORDER[entry.rank] > threshold_index
    ]

    if failures:
        worst = max(failures, key=lambda e: RANK_ORDER.get(e.rank, 0))
        location = f"{worst.path}:{worst.lineno}" if worst.lineno else worst.path
        print(
            f"::error::Radon found {len(failures)} block(s) worse than rank {fail_rank}. Worst: {location} ({worst.rank}, complexity {worst.complexity:.2f}).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
