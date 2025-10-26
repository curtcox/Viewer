#!/usr/bin/env python3
"""Generate the integration test summary used in CI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


DEFAULT_TAIL_LINES = 50


def tail_lines(path: Path, limit: int) -> Iterable[str]:
    """Return up to the last ``limit`` lines from ``path``."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return lines[-limit:]


def build_summary(log_path: Path | None, junit_path: Path | None, tail_count: int) -> str:
    lines: list[str] = ["### Integration tests", ""]

    if log_path and log_path.is_file():
        lines.append("```")
        lines.extend(line.rstrip("\n") for line in tail_lines(log_path, tail_count))
        lines.append("```")
        lines.append("")
        if junit_path:
            lines.append(f"JUnit XML: {junit_path}")
    else:
        lines.append("No integration test log was produced.")

    lines.append("")
    return "\n".join(lines)


def write_summary(content: str, summary_path: Path | None) -> None:
    if summary_path:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        print(content, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        type=Path,
        help="Path to the integration test log file.",
    )
    parser.add_argument(
        "--junit",
        type=Path,
        help="Path to the generated JUnit XML report.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="File to append the summary to. Defaults to the GITHUB_STEP_SUMMARY output in CI.",
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=DEFAULT_TAIL_LINES,
        help=f"Number of log lines to include. Defaults to {DEFAULT_TAIL_LINES}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_content = build_summary(args.log, args.junit, args.tail_lines)
    write_summary(summary_content, args.summary)


if __name__ == "__main__":
    main()
