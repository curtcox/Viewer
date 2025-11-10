#!/usr/bin/env python3
"""Build the static test report site from downloaded CI artifacts."""
# pylint: disable=too-many-lines  # Build script with comprehensive artifact processing (1005 lines)

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html import escape
from importlib import import_module
from pathlib import Path
from typing import Protocol, Sequence, cast


# Constants
MAX_DISPLAYED_ITEMS = 20

# Regex patterns for Gauge log parsing
REGEX_SPEC_FILE = re.compile(r"^([a-zA-Z0-9_/.-]+\.spec)\s*::")
REGEX_SCENARIO_NAME = re.compile(r"::\s*(.+?)(?:\s*->|\s*✖|$)")
REGEX_MISSING_STEP = re.compile(r"no step implementation matches|No step implementation matches", re.IGNORECASE)
REGEX_STEP_MATCH = re.compile(r"matches:\s*(.+)$", re.IGNORECASE)
REGEX_TOTAL_SCENARIOS = re.compile(r"Total scenarios:\s*(\d+)")
REGEX_PASSED_SCENARIOS = re.compile(r"Passed:\s*(\d+)")
REGEX_FAILED_SCENARIOS = re.compile(r"Failed:\s*(\d+)")

# Regex pattern for Pylint output
# Pattern: file.py:line:col: CODE: Message (symbolic-name)
REGEX_PYLINT_LINE = re.compile(
    r'^([^:]+):(\d+):(\d+):\s+([A-Z]\d{4}):\s+(.+?)\s+\(([a-z-]+)\)\s*$'
)

# HTML/CSS templates
BASE_CSS = """    body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }
    a { color: #0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }"""

COMMON_CSS = BASE_CSS + """
    pre { background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }
    .pylint-output { background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: monospace; white-space: pre-wrap; word-wrap: break-word; }
    .warning { background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 1rem; margin: 1rem 0; }
    .warning strong { color: #856404; }
    .warning ul { margin-top: 0.5rem; margin-bottom: 0.5rem; }"""

GAUGE_CSS = BASE_CSS + """
    h1 { font-size: 2rem; margin-bottom: 1rem; }
    h2 { font-size: 1.5rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
    h3 { font-size: 1.2rem; margin-top: 1rem; margin-bottom: 0.5rem; }
    ul { list-style: disc; padding-left: 1.5rem; }
    li { margin: 0.25rem 0; }
    code { background: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }"""

LANDING_CSS = BASE_CSS + """
    h1 { font-size: 2rem; margin-bottom: 1rem; }
    h2 { font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; border-bottom: 1px solid #e1e4e8; padding-bottom: 0.5rem; }
    ul { list-style: disc; padding-left: 1.5rem; }
    .job-list { list-style: none; padding: 0; margin: 1rem 0; }
    .job-item { display: flex; align-items: center; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #e1e4e8; border-radius: 6px; background: #f6f8fa; }
    .job-status { flex-shrink: 0; margin-right: 1rem; font-size: 1.5rem; }
    .job-status.success { color: #28a745; }
    .job-status.failure { color: #d73a49; }
    .job-status.skipped { color: #6a737d; }
    .job-icon { flex-shrink: 0; margin-right: 0.75rem; font-size: 1.2rem; }
    .job-info { flex-grow: 1; }
    .job-name { font-weight: 600; margin: 0; }
    .job-type { color: #586069; font-size: 0.9rem; margin: 0.25rem 0 0 0; }
    .job-link { margin-left: auto; }
    .screenshot-status { margin-top: 2rem; padding: 1rem; background: #fff8c5; border-left: 4px solid #9a6700; }
    .screenshot-status h2 { margin-top: 0; }
    .screenshot-status ul { margin-top: 0.5rem; }"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
{style}
  </style>
</head>
<body>
{body}
</body>
</html>"""


@dataclass
class GaugeSummary:
    """Structured data extracted from Gauge execution logs."""
    specs_run: list[str] = field(default_factory=list)
    specs_failed: list[str] = field(default_factory=list)
    missing_steps: list[str] = field(default_factory=list)
    failed_scenarios: list[str] = field(default_factory=list)
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios_count: int = 0


class EnhanceGaugeReport(Protocol):
    def __call__(
        self,
        gauge_base: Path,
        *,
        artifacts_subdir: str = ...,
        public_base_url: str | None = ...,
    ) -> bool:
        ...


def _load_enhance_gauge_report() -> EnhanceGaugeReport:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    module = import_module("tests.gauge_report")
    return cast(EnhanceGaugeReport, module.enhance_gauge_report)


enhance_gauge_report = _load_enhance_gauge_report()


def _html_list(items: list[str], limit: int = MAX_DISPLAYED_ITEMS, escape_items: bool = True) -> str:
    """Generate an HTML list from items, optionally limiting the display count."""
    if not items:
        return ""

    display_items = items[:limit]
    item_html = "".join(
        f"<li>{escape(item) if escape_items else item}</li>"
        for item in display_items
    )

    if len(items) > limit:
        item_html += f"<li>... and {len(items) - limit} more</li>"

    return item_html


def _html_list_code(items: list[str], limit: int = MAX_DISPLAYED_ITEMS) -> str:
    """Generate an HTML list with code-formatted items."""
    if not items:
        return ""

    display_items = items[:limit]
    item_html = "".join(f"<li><code>{escape(item)}</code></li>" for item in display_items)

    if len(items) > limit:
        item_html += f"<li>... and {len(items) - limit} more</li>"

    return item_html


def _render_html_page(title: str, body: str, css: str) -> str:
    """Render a complete HTML page using the template."""
    return HTML_TEMPLATE.format(title=title, style=css, body=body)


def _compose_public_url(base: str | None, segment: str) -> str | None:
    if not base:
        return None

    base = base.rstrip('/')
    segment = segment.strip('/')
    if not segment:
        return base or None
    return f"{base}/{segment}"


def _copy_artifacts(source: Path | None, destination: Path) -> None:
    """Copy an artifact directory into the destination if needed."""
    destination.mkdir(parents=True, exist_ok=True)

    if source is None:
        return

    source = source.resolve()
    destination = destination.resolve()

    if not source.exists():
        return

    if source == destination:
        return

    # When copying between distinct locations, clear the destination so stale
    # files from previous runs do not linger in the published site.
    if destination.exists():
        shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source, destination, dirs_exist_ok=True)



def _flatten_htmlcov(unit_tests_dir: Path) -> None:
    htmlcov_dir = unit_tests_dir / "htmlcov"
    if not htmlcov_dir.is_dir():
        return

    for item in htmlcov_dir.iterdir():
        target = unit_tests_dir / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), target)

    htmlcov_dir.rmdir()



def _flatten_gauge_reports(gauge_dir: Path) -> None:
    reports_dir = gauge_dir / "reports"
    html_report = reports_dir / "html-report"

    if not html_report.is_dir():
        return

    for item in html_report.iterdir():
        target = gauge_dir / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), target)

    shutil.rmtree(reports_dir)



def _build_integration_index(integration_dir: Path) -> None:
    integration_dir.mkdir(parents=True, exist_ok=True)

    log_path = integration_dir / "integration-tests.log"
    xml_path = integration_dir / "integration-tests-report.xml"
    index_path = integration_dir / "index.html"

    log_content = "No log output was captured."
    if log_path.exists():
        log_content = escape(log_path.read_text(encoding="utf-8"))

    xml_link = ""
    if xml_path.exists():
        xml_link = '<p><a href="integration-tests-report.xml">Download the JUnit XML report</a></p>'

    body = f"""  <h1>Integration test results</h1>
  {xml_link}
  <h2>Latest log excerpt</h2>
  <pre>{log_content}</pre>"""

    index_path.write_text(
        _render_html_page("Integration test results", body, COMMON_CSS),
        encoding="utf-8",
    )


def _build_property_summary(xml_path: Path) -> str:
    """Return an HTML summary snippet for a JUnit XML report."""

    def _get_int(attrib: dict[str, str], key: str) -> int:
        value = attrib.get(key)
        if value is None:
            return 0
        try:
            return int(float(value))
        except ValueError:
            return 0

    try:
        tree = ET.parse(xml_path)
    except (ET.ParseError, OSError):
        return "<p>Unable to parse the JUnit XML report.</p>"

    root = tree.getroot()
    metric_keys = ("tests", "failures", "errors", "skipped")

    counts = {key: 0 for key in metric_keys}
    if root.tag == "testsuite":
        counts = {key: _get_int(root.attrib, key) for key in metric_keys}
    elif root.tag == "testsuites":
        if any(key in root.attrib for key in metric_keys):
            counts = {key: _get_int(root.attrib, key) for key in metric_keys}
        else:
            for suite in root.findall("testsuite"):
                for key in metric_keys:
                    counts[key] += _get_int(suite.attrib, key)
    else:
        return "<p>Unrecognized JUnit XML structure.</p>"

    passed = max(
        counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
        0,
    )

    summary = [
        f"  <li>Total tests: {counts['tests']}</li>",
        f"  <li>Passed: {passed}</li>",
        f"  <li>Failures: {counts['failures']}</li>",
        f"  <li>Errors: {counts['errors']}</li>",
        f"  <li>Skipped: {counts['skipped']}</li>",
    ]

    return "<h2>Summary</h2><ul>\n" + "\n".join(summary) + "\n</ul>"


def _parse_gauge_log(log_path: Path) -> GaugeSummary:
    """Parse Gauge execution log and extract summary data."""
    summary = GaugeSummary()

    if not log_path.exists():
        return summary

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return summary

    lines = content.splitlines()
    current_spec: str | None = None

    for line in lines:
        line = line.strip()
        current_spec = _extract_spec_from_line(line, summary, current_spec)
        _detect_failed_scenario(line, summary, current_spec)
        _detect_missing_step(line, summary)
        _extract_scenario_statistics(line, summary)

    return summary


def _extract_spec_from_line(line: str, summary: GaugeSummary, current_spec: str | None) -> str | None:
    """Extract spec file path from a log line and update summary."""
    spec_match = REGEX_SPEC_FILE.match(line)
    if spec_match:
        spec_name = spec_match.group(1)
        if spec_name not in summary.specs_run:
            summary.specs_run.append(spec_name)
        return spec_name
    return current_spec


def _detect_failed_scenario(line: str, summary: GaugeSummary, current_spec: str | None) -> None:
    """Detect failed scenarios from a log line and update summary."""
    if current_spec and ("-> FAILED" in line or "✖" in line or "FAILED" in line):
        scenario_match = REGEX_SCENARIO_NAME.search(line)
        if scenario_match:
            scenario_name = scenario_match.group(1).strip()
            summary.failed_scenarios.append(f"{current_spec} :: {scenario_name}")
            if current_spec not in summary.specs_failed:
                summary.specs_failed.append(current_spec)


def _detect_missing_step(line: str, summary: GaugeSummary) -> None:
    """Detect missing step implementations from a log line and update summary."""
    if REGEX_MISSING_STEP.search(line):
        step_match = REGEX_STEP_MATCH.search(line)
        if step_match:
            missing_step = step_match.group(1).strip()
            if missing_step not in summary.missing_steps:
                summary.missing_steps.append(missing_step)


def _extract_scenario_statistics(line: str, summary: GaugeSummary) -> None:
    """Extract scenario statistics from a log line and update summary."""
    match = REGEX_TOTAL_SCENARIOS.search(line)
    if match:
        summary.total_scenarios = int(match.group(1))
        return

    match = REGEX_PASSED_SCENARIOS.search(line)
    if match:
        summary.passed_scenarios = int(match.group(1))
        return

    match = REGEX_FAILED_SCENARIOS.search(line)
    if match:
        summary.failed_scenarios_count = int(match.group(1))


def _format_gauge_summary_html(summary: GaugeSummary) -> str:
    """Format Gauge summary data as HTML."""
    summary_items = []
    if summary.specs_run:
        summary_items.append(f"  <li>Total specifications: {len(summary.specs_run)}</li>")
    if summary.total_scenarios > 0:
        summary_items.append(f"  <li>Total scenarios: {summary.total_scenarios}</li>")
        summary_items.append(f"  <li>Passed scenarios: {summary.passed_scenarios}</li>")
        summary_items.append(f"  <li>Failed scenarios: {summary.failed_scenarios_count}</li>")

    summary_html = "<h2>Summary</h2><ul>\n" + "\n".join(summary_items) + "\n</ul>" if summary_items else ""

    details = []
    if summary.specs_run:
        spec_list = _html_list(sorted(summary.specs_run))
        details.append(f"<h3>Specifications executed ({len(summary.specs_run)})</h3><ul>{spec_list}</ul>")

    if summary.specs_failed:
        failed_list = _html_list(sorted(set(summary.specs_failed)))
        details.append(f"<h3>Failed specifications ({len(summary.specs_failed)})</h3><ul>{failed_list}</ul>")

    if summary.failed_scenarios:
        scenario_list = _html_list(summary.failed_scenarios)
        details.append(f"<h3>Failed scenarios ({len(summary.failed_scenarios)})</h3><ul>{scenario_list}</ul>")

    if summary.missing_steps:
        step_list = _html_list_code(summary.missing_steps)
        details.append(f"<h3>Missing step implementations ({len(summary.missing_steps)})</h3><ul>{step_list}</ul>")

    return summary_html + "\n" + "\n".join(details)


def _build_gauge_summary(log_path: Path) -> str:
    """Return an HTML summary snippet for Gauge execution results."""
    if not log_path.exists():
        return "<p>No Gauge execution log was found.</p>"

    summary = _parse_gauge_log(log_path)
    if not summary.specs_run:
        return "<p>No specifications were executed.</p>"

    return _format_gauge_summary_html(summary)


def _build_gauge_index(gauge_dir: Path) -> None:
    """Build an index page for Gauge reports with summary."""
    gauge_dir.mkdir(parents=True, exist_ok=True)

    log_path = gauge_dir / "gauge-execution.log"
    index_path = gauge_dir / "index.html"
    original_index = gauge_dir / "index_original.html"

    # Preserve the original Gauge HTML report index if it exists
    # (it may have been moved here by _flatten_gauge_reports)
    if index_path.exists() and not original_index.exists():
        # Check if it's actually a Gauge HTML report (contains gauge-specific content)
        try:
            content = index_path.read_text(encoding="utf-8", errors="replace")
            if "gauge" in content.lower() and ("executionResult" in content or "specs" in content.lower()):
                shutil.move(index_path, original_index)
        except OSError:
            pass

    summary_html = _build_gauge_summary(log_path)

    # Add link to original Gauge report if it exists
    original_link = ""
    if original_index.exists():
        original_link = '<p><a href="index_original.html">View full Gauge HTML report</a></p>'

    body = f"""  <h1>Gauge specification results</h1>
  {original_link}
  {summary_html}"""

    index_path.write_text(
        _render_html_page("Gauge specification results", body, GAUGE_CSS),
        encoding="utf-8",
    )


def _build_property_index(property_dir: Path) -> None:
    property_dir.mkdir(parents=True, exist_ok=True)

    log_path = property_dir / "property-tests.log"
    xml_path = property_dir / "property-tests-report.xml"
    index_path = property_dir / "index.html"

    log_content = "No log output was captured."
    if log_path.exists():
        log_content = escape(log_path.read_text(encoding="utf-8"))

    summary_html = "<p>No JUnit XML report was generated.</p>"
    xml_link = ""
    if xml_path.exists():
        summary_html = _build_property_summary(xml_path)
        xml_link = '<p><a href="property-tests-report.xml">Download the JUnit XML report</a></p>'

    body = f"""  <h1>Property test results</h1>
  {xml_link}
  {summary_html}
  <h2>Latest log output</h2>
  <pre>{log_content}</pre>"""

    index_path.write_text(
        _render_html_page("Property test results", body, COMMON_CSS),
        encoding="utf-8",
    )


def _enhance_pylint_output(output_text: str, github_repo: str = "curtcox/Viewer", github_branch: str = "main") -> str:
    """Enhance pylint output with links to rule documentation and source code.

    Args:
        output_text: Raw pylint output text
        github_repo: GitHub repository in format "owner/repo"
        github_branch: Branch name for GitHub links

    Returns:
        HTML-formatted output with links
    """
    if not output_text.strip():
        return escape(output_text)

    lines = output_text.splitlines()
    enhanced_lines = []

    for line in lines:
        match = REGEX_PYLINT_LINE.match(line)
        if match:
            file_path = match.group(1)
            line_num = match.group(2)
            col_num = match.group(3)
            msg_code = match.group(4)
            message = match.group(5)
            symbolic_name = match.group(6)

            # Create GitHub source link
            github_url = f"https://github.com/{github_repo}/blob/{github_branch}/{file_path}#L{line_num}"
            source_link = f'<a href="{github_url}">{escape(file_path)}:{line_num}:{col_num}</a>'

            # Create Pylint documentation link
            pylint_url = f"https://pylint.pycqa.org/en/latest/user_guide/messages/{symbolic_name}.html"
            rule_link = f'<a href="{pylint_url}">{escape(msg_code)}</a>'

            enhanced_line = f'{source_link}: {rule_link}: {escape(message)} ({escape(symbolic_name)})'
            enhanced_lines.append(enhanced_line)
        else:
            # Not a pylint message line, just escape it
            enhanced_lines.append(escape(line))

    return '<br>\n'.join(enhanced_lines)


def _build_linter_index(linter_dir: Path, title: str, linter_name: str, job_status: str | None = None) -> None:
    """Build an index page for linter reports (Pylint, ShellCheck, Hadolint).

    Args:
        linter_dir: Directory containing the linter artifacts
        title: Page title for the report
        linter_name: Name of the linter (Pylint, ShellCheck, or Hadolint)
        job_status: Optional job status ("success", "failure", "skipped") for better messaging
    """
    linter_dir.mkdir(parents=True, exist_ok=True)

    summary_path = linter_dir / "summary.txt"
    output_path = linter_dir / "output.txt"
    index_path = linter_dir / "index.html"

    # Check if artifacts exist and have content
    summary_exists = summary_path.exists()
    output_exists = output_path.exists()
    has_summary_content = False
    has_output_content = False

    summary_html = "<p>No summary available.</p>"
    if summary_exists:
        summary_content = summary_path.read_text(encoding="utf-8")
        summary_lines = summary_content.strip().split("\n")
        summary_items = "".join(f"<li>{escape(line)}</li>" for line in summary_lines if line.strip())
        if summary_items:  # Only show summary if we have non-empty items
            summary_html = f"<h2>Summary</h2><ul>{summary_items}</ul>"
            has_summary_content = True

    output_content = "No output was captured."
    if output_exists:
        output_text = output_path.read_text(encoding="utf-8")
        if output_text.strip():
            # Enhance pylint output with links
            if linter_name == "Pylint":
                output_content = _enhance_pylint_output(output_text)
            else:
                output_content = escape(output_text)
            has_output_content = True
        else:
            if job_status == "failure":
                output_content = "No output was captured."
            else:
                output_content = "All checks passed - no issues found."

    # Provide context-aware messaging when job status doesn't match artifacts
    if job_status == "failure" and not has_summary_content and not has_output_content:
        # Job failed but we have no artifacts to show why
        summary_html = f"""<div class="warning">
  <p><strong>⚠ Check Failed</strong></p>
  <p>The {escape(linter_name)} check failed, but detailed results are not available.</p>
  <p>This typically indicates the check encountered an error before completion, such as:</p>
  <ul>
    <li>The linter tool failed to install or run</li>
    <li>A timeout or resource limit was exceeded</li>
    <li>An unexpected error occurred during execution</li>
  </ul>
  <p>Check the CI workflow logs for more details.</p>
</div>"""
        output_content = ""
    elif job_status == "skipped":
        summary_html = f"<p>The {escape(linter_name)} check was skipped.</p>"
        output_content = ""

    # Use <div> with pre-like styling for enhanced output instead of <pre> tag
    output_tag = "div" if linter_name == "Pylint" else "pre"
    output_class = ' class="pylint-output"' if linter_name == "Pylint" else ""

    # Only show output section if we have content to display
    output_section = ""
    if output_content:
        output_section = f"""<h2>{escape(linter_name)} output</h2>
  <{output_tag}{output_class}>{output_content}</{output_tag}>"""

    body = f"""  <h1>{escape(title)}</h1>
  {summary_html}
  {output_section}"""

    index_path.write_text(
        _render_html_page(title, body, COMMON_CSS),
        encoding="utf-8",
    )


def _build_test_index_page(test_index_dir: Path) -> None:
    """Build an index page for Test Index with link to TEST_INDEX.md."""
    test_index_dir.mkdir(parents=True, exist_ok=True)

    summary_path = test_index_dir / "summary.txt"
    output_path = test_index_dir / "output.txt"
    test_index_md = test_index_dir / "TEST_INDEX.md"
    index_path = test_index_dir / "index.html"

    summary_html = "<p>No summary available.</p>"
    if summary_path.exists():
        summary_content = summary_path.read_text(encoding="utf-8")
        summary_lines = summary_content.strip().split("\n")
        summary_items = "".join(f"<li>{escape(line)}</li>" for line in summary_lines if line.strip())
        if summary_items:  # Only show summary if we have non-empty items
            summary_html = f"<h2>Summary</h2><ul>{summary_items}</ul>"

    test_index_link = ""
    if test_index_md.exists():
        test_index_link = '<p><a href="TEST_INDEX.md">View TEST_INDEX.md</a></p>'

    output_content = "No output was captured."
    if output_path.exists():
        output_text = output_path.read_text(encoding="utf-8")
        if output_text.strip():
            output_content = escape(output_text)
        else:
            output_content = "Test index validation passed."

    body = f"""  <h1>Test Index Validation</h1>
  {test_index_link}
  {summary_html}
  <h2>Validation output</h2>
  <pre>{output_content}</pre>"""

    index_path.write_text(
        _render_html_page("Test Index Validation", body, COMMON_CSS),
        encoding="utf-8",
    )


def _collect_screenshot_issues(
    gauge_dir: Path, *, artifacts_subdir: str = "secureapp-artifacts"
) -> tuple[int, list[str]]:
    artifacts_dir = gauge_dir / artifacts_subdir
    if not artifacts_dir.is_dir():
        return 0, []

    placeholder_count = 0
    reasons: list[str] = []

    for json_path in sorted(artifacts_dir.glob("*.json")):
        try:
            metadata = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        screenshot_info = metadata.get("screenshot")
        if not isinstance(screenshot_info, dict):
            continue
        if screenshot_info.get("captured"):
            continue

        placeholder_count += 1

        details = screenshot_info.get("details")
        if isinstance(details, str):
            reasons.append(details)
        elif isinstance(details, list):
            for entry in details:
                if isinstance(entry, str):
                    reasons.append(entry)
                else:
                    reasons.append(str(entry))

    normalized = [reason.strip() for reason in reasons if reason and reason.strip()]
    unique_reasons = list(dict.fromkeys(normalized))
    return placeholder_count, unique_reasons


def _format_screenshot_notice(count: int, reasons: Sequence[str]) -> str | None:
    if count <= 0:
        return None

    count_text = "capture" if count == 1 else "captures"
    intro = (
        f"  <section class=\"screenshot-status\">\n"
        "    <h2>Gauge screenshot status</h2>\n"
        f"    <p>Browser screenshots were unavailable for {count} {count_text}. "
        "The shared placeholder image has been published in their place.</p>\n"
    )

    if reasons:
        reason_items = "\n".join(
            f"      <li>{escape(reason)}</li>" for reason in reasons
        )
        reason_block = (
            "    <p>Reported reasons:</p>\n"
            "    <ul>\n"
            f"{reason_items}\n"
            "    </ul>\n"
        )
    else:
        reason_block = "    <p>No specific error details were recorded.</p>\n"

    guidance_block = (
        "    <p>Gauge stores per-step artifacts under "
        "<code>gauge-specs/secureapp-artifacts</code>. "
        "Each <code>.json</code> file in that directory preserves the raw error "
        "messages listed above, and the screenshot helper lives in "
        "<code>step_impl/artifacts.py</code>, where pyppeteer launches a "
        "headless Chromium instance to render the HTML under test.</p>\n"
        "    <p>To restore real browser screenshots:</p>\n"
        "    <ol>\n"
        "      <li>Install the project dependencies so <code>pyppeteer</code> is "
        "available (for example, <code>pip install -r requirements.txt</code>).</li>\n"
        "      <li>Download Chromium inside the environment that runs the Gauge "
        "suite by executing <code>pyppeteer-install</code> before "
        "<code>./test-gauge</code>.</li>\n"
        "      <li>Ensure the runtime image provides the shared libraries that "
        "Chromium requires. On the Ubuntu-based CI container this means adding "
        "<code>apt-get install -y --no-install-recommends libnss3 libatk1.0-0 "
        "libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 "
        "libxrandr2 libgbm1 libgtk-3-0 libasound2 fonts-liberation</code>. "
        "Missing these packages produces the \"Browser closed unexpectedly\" "
        "error shown in the report.</li>\n"
        "      <li>Re-run <code>./test-gauge</code> locally (or rerun the GitHub "
        "Actions <code>gauge-specs</code> job) and confirm that new PNG files "
        "appear next to the JSON metadata in "
        "<code>gauge-specs/secureapp-artifacts</code>.</li>\n"
        "    </ol>\n"
        "    <p>Once those steps succeed, rebuilding the published site will "
        "replace the placeholder art with the captured browser screenshots.</p>\n"
    )

    closing = "  </section>"
    return intro + reason_block + guidance_block + closing


@dataclass
class JobMetadata:
    """Metadata for a CI job."""
    name: str
    icon: str
    check_type: str
    report_link: str | None = None


def _load_job_statuses(job_statuses_path: Path | None) -> dict[str, str]:
    """Load job statuses from JSON file."""
    if job_statuses_path is None or not job_statuses_path.exists():
        return {}

    try:
        return json.loads(job_statuses_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _get_job_metadata() -> dict[str, JobMetadata]:
    """Define metadata for all CI jobs."""
    return {
        "ruff": JobMetadata(
            name="Ruff",
            icon="⚡",
            check_type="Python Linter & Formatter",
            report_link=None
        ),
        "pylint": JobMetadata(
            name="Pylint",
            icon="🔍",
            check_type="Python Code Quality",
            report_link="pylint/index.html"
        ),
        "mypy": JobMetadata(
            name="Mypy",
            icon="📝",
            check_type="Python Type Checker",
            report_link=None
        ),
        "radon": JobMetadata(
            name="Radon",
            icon="📊",
            check_type="Code Complexity Analysis",
            report_link="radon/index.html"
        ),
        "vulture": JobMetadata(
            name="Vulture",
            icon="🦅",
            check_type="Dead Code Detection",
            report_link="vulture/index.html"
        ),
        "python-smells": JobMetadata(
            name="Python Smells",
            icon="👃",
            check_type="Code Smell Detection",
            report_link="python-smells/index.html"
        ),
        "shellcheck": JobMetadata(
            name="ShellCheck",
            icon="🐚",
            check_type="Shell Script Linter",
            report_link="shellcheck/index.html"
        ),
        "hadolint": JobMetadata(
            name="Hadolint",
            icon="🐳",
            check_type="Dockerfile Linter",
            report_link="hadolint/index.html"
        ),
        "eslint": JobMetadata(
            name="ESLint",
            icon="📜",
            check_type="JavaScript/TypeScript Linter",
            report_link=None
        ),
        "stylelint": JobMetadata(
            name="Stylelint",
            icon="🎨",
            check_type="CSS Linter",
            report_link=None
        ),
        "uncss": JobMetadata(
            name="UNCSS",
            icon="✂️",
            check_type="Unused CSS Checker",
            report_link=None
        ),
        "test-index": JobMetadata(
            name="Test Index",
            icon="📑",
            check_type="Test Index Validation",
            report_link="test-index/index.html"
        ),
        "unit-tests": JobMetadata(
            name="Unit Tests",
            icon="🧪",
            check_type="Unit Tests & Coverage",
            report_link="unit-tests/index.html"
        ),
        "property-tests": JobMetadata(
            name="Property Tests",
            icon="🔬",
            check_type="Property-Based Testing",
            report_link="property-tests/index.html"
        ),
        "integration-tests": JobMetadata(
            name="Integration Tests",
            icon="🔗",
            check_type="Integration Testing",
            report_link="integration-tests/index.html"
        ),
        "gauge-specs": JobMetadata(
            name="Gauge",
            icon="📏",
            check_type="BDD Specifications",
            report_link="gauge-specs/index.html"
        ),
    }


def _format_job_list(job_statuses: dict[str, str]) -> str:
    """Generate HTML for the job list with status indicators."""
    if not job_statuses:
        return "<p>No job status information available.</p>"

    job_metadata = _get_job_metadata()
    html_parts = ['<ul class="job-list">']

    for job_id, status in job_statuses.items():
        metadata = job_metadata.get(job_id)
        if not metadata:
            continue

        # Determine status indicator and CSS class
        if status == "success":
            status_icon = "●"
            status_class = "success"
        elif status == "failure":
            status_icon = "✖"
            status_class = "failure"
        elif status == "skipped":
            status_icon = "○"
            status_class = "skipped"
        else:
            status_icon = "?"
            status_class = "skipped"

        # Build the job item HTML
        link_html = ""
        if metadata.report_link:
            link_html = f'<div class="job-link"><a href="{metadata.report_link}">View Report →</a></div>'

        html_parts.append(f'''  <li class="job-item">
    <span class="job-status {status_class}">{status_icon}</span>
    <span class="job-icon">{metadata.icon}</span>
    <div class="job-info">
      <p class="job-name">{escape(metadata.name)}</p>
      <p class="job-type">{escape(metadata.check_type)}</p>
    </div>
    {link_html}
  </li>''')

    html_parts.append('</ul>')
    return '\n'.join(html_parts)


def _write_landing_page(site_dir: Path, *, screenshot_notice: str | None = None, job_statuses: dict[str, str] | None = None) -> None:
    index_path = site_dir / "index.html"
    notice_html = (screenshot_notice + "\n") if screenshot_notice else ""

    if job_statuses is None:
        job_statuses = {}

    job_list_html = _format_job_list(job_statuses)

    body = f"""  <h1>SecureApp Test Reports</h1>
  <h2>CI Check Results</h2>
{job_list_html}
{notice_html}"""

    index_path.write_text(
        _render_html_page("SecureApp Test Reports", body, LANDING_CSS),
        encoding="utf-8",
    )



def build_site(
    *,
    unit_tests_artifacts: Path | None,
    gauge_artifacts: Path | None,
    integration_artifacts: Path | None,
    property_artifacts: Path | None,
    radon_artifacts: Path | None,
    vulture_artifacts: Path | None,
    python_smells_artifacts: Path | None,
    pylint_artifacts: Path | None,
    shellcheck_artifacts: Path | None,
    hadolint_artifacts: Path | None,
    test_index_artifacts: Path | None,
    job_statuses_path: Path | None,
    output_dir: Path,
    public_base_url: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_tests_dir = output_dir / "unit-tests"
    gauge_dir = output_dir / "gauge-specs"
    integration_dir = output_dir / "integration-tests"
    property_dir = output_dir / "property-tests"
    radon_dir = output_dir / "radon"
    vulture_dir = output_dir / "vulture"
    python_smells_dir = output_dir / "python-smells"
    pylint_dir = output_dir / "pylint"
    shellcheck_dir = output_dir / "shellcheck"
    hadolint_dir = output_dir / "hadolint"
    test_index_dir = output_dir / "test-index"

    _copy_artifacts(unit_tests_artifacts, unit_tests_dir)
    _copy_artifacts(gauge_artifacts, gauge_dir)
    _copy_artifacts(integration_artifacts, integration_dir)
    _copy_artifacts(property_artifacts, property_dir)
    _copy_artifacts(radon_artifacts, radon_dir)
    _copy_artifacts(vulture_artifacts, vulture_dir)
    _copy_artifacts(python_smells_artifacts, python_smells_dir)
    _copy_artifacts(pylint_artifacts, pylint_dir)
    _copy_artifacts(shellcheck_artifacts, shellcheck_dir)
    _copy_artifacts(hadolint_artifacts, hadolint_dir)
    _copy_artifacts(test_index_artifacts, test_index_dir)

    _flatten_htmlcov(unit_tests_dir)
    _flatten_gauge_reports(gauge_dir)

    # Load job statuses early so we can pass them to report builders for context-aware messaging
    job_statuses = _load_job_statuses(job_statuses_path)

    gauge_public_base = _compose_public_url(public_base_url, "gauge-specs")
    enhance_gauge_report(gauge_dir, public_base_url=gauge_public_base)
    placeholder_count, screenshot_reasons = _collect_screenshot_issues(gauge_dir)
    screenshot_notice = _format_screenshot_notice(placeholder_count, screenshot_reasons)
    _build_gauge_index(gauge_dir)
    _build_integration_index(integration_dir)
    _build_property_index(property_dir)
    _build_linter_index(pylint_dir, "Pylint Report", "Pylint", job_statuses.get("pylint"))
    _build_linter_index(python_smells_dir, "Python Smells Report", "Python Smells", job_statuses.get("python-smells"))
    _build_linter_index(shellcheck_dir, "ShellCheck Report", "ShellCheck", job_statuses.get("shellcheck"))
    _build_linter_index(hadolint_dir, "Hadolint Report", "Hadolint", job_statuses.get("hadolint"))
    _build_test_index_page(test_index_dir)
    _write_landing_page(output_dir, screenshot_notice=screenshot_notice, job_statuses=job_statuses)



def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the static test report site.")
    parser.add_argument(
        "--unit-tests-artifacts",
        type=Path,
        default=None,
        help="Directory containing the unit test coverage artifact.",
    )
    parser.add_argument(
        "--gauge-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Gauge HTML report artifact.",
    )
    parser.add_argument(
        "--integration-artifacts",
        type=Path,
        default=None,
        help="Directory containing the integration test artifact.",
    )
    parser.add_argument(
        "--property-artifacts",
        type=Path,
        default=None,
        help="Directory containing the property test artifacts.",
    )
    parser.add_argument(
        "--radon-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Radon complexity report artifacts.",
    )
    parser.add_argument(
        "--vulture-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Vulture dead code report artifacts.",
    )
    parser.add_argument(
        "--python-smells-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Python Smells report artifacts.",
    )
    parser.add_argument(
        "--pylint-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Pylint report artifacts.",
    )
    parser.add_argument(
        "--shellcheck-artifacts",
        type=Path,
        default=None,
        help="Directory containing the ShellCheck report artifacts.",
    )
    parser.add_argument(
        "--hadolint-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Hadolint report artifacts.",
    )
    parser.add_argument(
        "--test-index-artifacts",
        type=Path,
        default=None,
        help="Directory containing the Test Index artifacts.",
    )
    parser.add_argument(
        "--job-statuses",
        type=Path,
        default=None,
        help="JSON file containing the status of all CI jobs.",
    )
    parser.add_argument(
        "--public-base-url",
        default="https://curtcox.github.io/Viewer",
        help="Base URL where the report site is published.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory where the site should be written.",
    )
    return parser.parse_args(argv)



def main(argv: Sequence[str] | None = None) -> int:
    parsed = parse_args(argv)

    build_site(
        unit_tests_artifacts=parsed.unit_tests_artifacts,
        gauge_artifacts=parsed.gauge_artifacts,
        integration_artifacts=parsed.integration_artifacts,
        property_artifacts=parsed.property_artifacts,
        radon_artifacts=parsed.radon_artifacts,
        vulture_artifacts=parsed.vulture_artifacts,
        python_smells_artifacts=parsed.python_smells_artifacts,
        pylint_artifacts=parsed.pylint_artifacts,
        shellcheck_artifacts=parsed.shellcheck_artifacts,
        hadolint_artifacts=parsed.hadolint_artifacts,
        test_index_artifacts=parsed.test_index_artifacts,
        job_statuses_path=parsed.job_statuses,
        output_dir=parsed.output,
        public_base_url=parsed.public_base_url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
