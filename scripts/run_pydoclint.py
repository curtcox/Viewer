#!/usr/bin/env python3
"""Generate pydoclint docstring quality reports for CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Sequence


@dataclass
class DocstringIssue:
    """Represents a single docstring issue from pydoclint."""
    path: str
    line: int
    code: str
    message: str


class PydoclintError(RuntimeError):
    """Raised when the pydoclint command fails."""


def _run_command(command: list[str]) -> tuple[str, str, int]:
    """Execute a command and return stdout, stderr, and exit code."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        raise PydoclintError(f"Failed to run command: {' '.join(command)}") from exc


def _parse_pydoclint_output(output: str) -> list[DocstringIssue]:
    """Parse pydoclint output into structured issues.
    
    Example format:
    file.py
        123: DOC101: Function `foo`: Docstring contains fewer arguments than in function signature.
    """
    issues: list[DocstringIssue] = []
    current_file = ""
    
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
            
        # Check if this is a file path line (no leading spaces)
        if line and not line[0].isspace():
            current_file = line.strip()
            continue
            
        # Parse issue line (has leading spaces)
        if ':' in line and current_file:
            try:
                # Format: "    123: DOC101: Message"
                parts = line.strip().split(':', 3)
                if len(parts) >= 3:
                    line_num = int(parts[0].strip())
                    code = parts[1].strip()
                    message = parts[2].strip() if len(parts) > 2 else ""
                    
                    issue = DocstringIssue(
                        path=current_file,
                        line=line_num,
                        code=code,
                        message=message,
                    )
                    issues.append(issue)
            except (ValueError, IndexError):
                continue
    
    return issues


def _categorize_issues(issues: list[DocstringIssue]) -> dict[str, list[DocstringIssue]]:
    """Group issues by their error code."""
    categories: dict[str, list[DocstringIssue]] = {}
    for issue in issues:
        if issue.code not in categories:
            categories[issue.code] = []
        categories[issue.code].append(issue)
    return categories


def _format_markdown_summary(issues: list[DocstringIssue]) -> str:
    """Generate a markdown summary of pydoclint findings."""
    if not issues:
        return "## Pydoclint Report\n\n✅ No docstring issues detected!"
    
    unique_files = len({issue.path for issue in issues})
    categories = _categorize_issues(issues)
    
    lines = [
        "## Pydoclint Report",
        "",
        f"Found **{len(issues)}** docstring issue(s) across **{unique_files}** file(s).",
        "",
        "### Issues by type",
        "",
    ]
    
    for code in sorted(categories.keys()):
        count = len(categories[code])
        lines.append(f"- `{code}`: {count} issue(s)")
    
    return "\n".join(lines)


def _format_html_report(issues: list[DocstringIssue]) -> str:
    """Generate an HTML report of pydoclint findings."""
    
    def _render_rows() -> str:
        if not issues:
            return "      <tr><td colspan=\"4\">No docstring issues detected! 🎉</td></tr>"
        
        rows: list[str] = []
        for issue in sorted(issues, key=lambda i: (i.path, i.line)):
            rows.append(
                f"      <tr><td>{escape(issue.path)}</td>"
                f"<td class=\"numeric\">{issue.line}</td>"
                f"<td>{escape(issue.code)}</td>"
                f"<td>{escape(issue.message)}</td></tr>"
            )
        return "\n".join(rows)
    
    categories = _categorize_issues(issues)
    unique_files = len({issue.path for issue in issues})
    
    summary_text = (
        f"Found {len(issues)} docstring issue(s) across {unique_files} file(s)."
        if issues else
        "No docstring issues detected!"
    )
    
    categories_rows = ""
    if categories:
        cat_rows = []
        for code in sorted(categories.keys()):
            count = len(categories[code])
            cat_rows.append(f"      <tr><td>{escape(code)}</td><td class=\"numeric\">{count}</td></tr>")
        categories_rows = f"""
  <section>
    <h2>Summary by type</h2>
    <table>
      <thead>
        <tr><th>Error Code</th><th>Count</th></tr>
      </thead>
      <tbody>
{chr(10).join(cat_rows)}
      </tbody>
    </table>
  </section>"""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Pydoclint docstring quality report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    h1 {{ font-size: 2rem; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }}
    th {{ background: #f6f8fa; }}
    td.numeric {{ text-align: right; }}
    section {{ margin-top: 2rem; }}
    .summary {{ background: #f1f8ff; border-left: 4px solid #0969da; padding: 1rem; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Pydoclint docstring quality report</h1>
  <div class="summary">
    <p>{escape(summary_text)} Pydoclint checks Python docstring styles and ensures
    they match function signatures. See <a href="https://github.com/jsh9/pydoclint">pydoclint documentation</a>
    for more information.</p>
  </div>{categories_rows}
  <section>
    <h2>Docstring issues</h2>
    <table>
      <thead>
        <tr><th>File</th><th>Line</th><th>Code</th><th>Message</th></tr>
      </thead>
      <tbody>
{_render_rows()}
      </tbody>
    </table>
  </section>
</body>
</html>
"""


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(argv: Sequence[str] | None = None) -> int:
    """Run pydoclint and generate reports."""
    parser = argparse.ArgumentParser(description="Run pydoclint and publish docstring quality reports.")
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
        "--paths",
        nargs="*",
        default=["."],
        help="Paths to analyze. Defaults to current directory.",
    )
    
    args = parser.parse_args(argv)
    
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build pydoclint command
    # Exclude common directories that shouldn't be checked
    exclude_pattern = r"\.git|\.tox|venv|env|\.venv|node_modules|__pycache__|\.pytest_cache|htmlcov|reports|site"
    command = ["pydoclint", "--quiet", "--exclude", exclude_pattern] + args.paths
    
    # Run pydoclint
    output, stderr, exit_code = _run_command(command)
    
    # pydoclint outputs to stderr, not stdout
    # Combine both for parsing, but check for real errors
    combined_output = output + stderr
    
    # pydoclint exits with 0 for success, non-zero for issues found or errors
    # Check if it's a real error (not just findings)
    if exit_code != 0 and combined_output.strip():
        # Check if it's a real error
        if any(indicator in combined_output.lower() for indicator in ["exception", "traceback", "usage:"]):
            error_msg = f"Pydoclint command failed with exit code {exit_code}."
            if combined_output.strip():
                error_msg = f"{error_msg}\nOutput: {combined_output.strip()}"
            raise PydoclintError(error_msg)
    
    # Parse the pydoclint output (from combined stdout + stderr)
    issues = _parse_pydoclint_output(combined_output)
    
    # Generate reports
    markdown = _format_markdown_summary(issues)
    html = _format_html_report(issues)
    
    _write_file(output_dir / "summary.md", markdown)
    _write_file(output_dir / "index.html", html)
    _write_file(output_dir / "output.txt", combined_output)
    
    if args.summary_file:
        _write_file(args.summary_file, markdown)
    
    print(markdown)
    
    # Report findings but don't fail the build
    if issues:
        print(
            f"::warning::Pydoclint found {len(issues)} docstring issue(s). "
            f"Review the report for details.",
            file=sys.stderr,
        )
    
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
