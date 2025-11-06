#!/usr/bin/env python3
"""Build the static test report site from downloaded CI artifacts."""

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

# HTML/CSS templates
BASE_CSS = """    body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }
    a { color: #0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }"""

COMMON_CSS = BASE_CSS + """
    pre { background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }"""

GAUGE_CSS = BASE_CSS + """
    h1 { font-size: 2rem; margin-bottom: 1rem; }
    h2 { font-size: 1.5rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
    h3 { font-size: 1.2rem; margin-top: 1rem; margin-bottom: 0.5rem; }
    ul { list-style: disc; padding-left: 1.5rem; }
    li { margin: 0.25rem 0; }
    code { background: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }"""

LANDING_CSS = BASE_CSS + """
    h1 { font-size: 2rem; margin-bottom: 1rem; }
    ul { list-style: disc; padding-left: 1.5rem; }
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


def _write_landing_page(site_dir: Path, *, screenshot_notice: str | None = None) -> None:
    index_path = site_dir / "index.html"
    notice_html = (screenshot_notice + "\n") if screenshot_notice else ""

    body = f"""  <h1>SecureApp Test Reports</h1>
  <ul>
    <li><a href="unit-tests/index.html">Unit test coverage report</a></li>
    <li><a href="integration-tests/index.html">Integration test results</a></li>
    <li><a href="gauge-specs/index.html">Gauge HTML report</a></li>
    <li><a href="property-tests/index.html">Property test results</a></li>
    <li><a href="radon/index.html">Radon complexity report</a></li>
  </ul>
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
    output_dir: Path,
    public_base_url: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_tests_dir = output_dir / "unit-tests"
    gauge_dir = output_dir / "gauge-specs"
    integration_dir = output_dir / "integration-tests"
    property_dir = output_dir / "property-tests"
    radon_dir = output_dir / "radon"

    _copy_artifacts(unit_tests_artifacts, unit_tests_dir)
    _copy_artifacts(gauge_artifacts, gauge_dir)
    _copy_artifacts(integration_artifacts, integration_dir)
    _copy_artifacts(property_artifacts, property_dir)
    _copy_artifacts(radon_artifacts, radon_dir)

    _flatten_htmlcov(unit_tests_dir)
    _flatten_gauge_reports(gauge_dir)

    gauge_public_base = _compose_public_url(public_base_url, "gauge-specs")
    enhance_gauge_report(gauge_dir, public_base_url=gauge_public_base)
    placeholder_count, screenshot_reasons = _collect_screenshot_issues(gauge_dir)
    screenshot_notice = _format_screenshot_notice(placeholder_count, screenshot_reasons)
    _build_gauge_index(gauge_dir)
    _build_integration_index(integration_dir)
    _build_property_index(property_dir)
    _write_landing_page(output_dir, screenshot_notice=screenshot_notice)



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
        output_dir=parsed.output,
        public_base_url=parsed.public_base_url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
