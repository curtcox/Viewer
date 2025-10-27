#!/usr/bin/env python3
"""Build the static test report site from downloaded CI artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from html import escape
from importlib import import_module
from pathlib import Path
from typing import Protocol, Sequence, cast


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

    index_path.write_text(
        """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Integration test results</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Integration test results</h1>
  {xml_link}
  <h2>Latest log excerpt</h2>
  <pre>{log_content}</pre>
</body>
</html>
""".format(xml_link=xml_link, log_content=log_content),
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

    index_path.write_text(
        """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Property test results</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Property test results</h1>
  {xml_link}
  {summary_html}
  <h2>Latest log output</h2>
  <pre>{log_content}</pre>
</body>
</html>
""".format(xml_link=xml_link, summary_html=summary_html, log_content=log_content),
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
    index_path.write_text(
        """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>SecureApp Test Reports</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.6; }}
    h1 {{ font-size: 2rem; margin-bottom: 1rem; }}
    ul {{ list-style: disc; padding-left: 1.5rem; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .screenshot-status {{ margin-top: 2rem; padding: 1rem; background: #fff8c5; border-left: 4px solid #9a6700; }}
    .screenshot-status h2 {{ margin-top: 0; }}
    .screenshot-status ul {{ margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>SecureApp Test Reports</h1>
  <ul>
    <li><a href=\"unit-tests/index.html\">Unit test coverage report</a></li>
    <li><a href=\"integration-tests/index.html\">Integration test results</a></li>
    <li><a href=\"gauge-specs/index.html\">Gauge HTML report</a></li>
    <li><a href=\"property-tests/index.html\">Property test results</a></li>
  </ul>
{notice_html}
</body>
</html>
""".format(notice_html=notice_html),
        encoding="utf-8",
    )



def build_site(
    *,
    unit_tests_artifacts: Path | None,
    gauge_artifacts: Path | None,
    integration_artifacts: Path | None,
    property_artifacts: Path | None,
    output_dir: Path,
    public_base_url: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_tests_dir = output_dir / "unit-tests"
    gauge_dir = output_dir / "gauge-specs"
    integration_dir = output_dir / "integration-tests"
    property_dir = output_dir / "property-tests"

    _copy_artifacts(unit_tests_artifacts, unit_tests_dir)
    _copy_artifacts(gauge_artifacts, gauge_dir)
    _copy_artifacts(integration_artifacts, integration_dir)
    _copy_artifacts(property_artifacts, property_dir)

    _flatten_htmlcov(unit_tests_dir)
    _flatten_gauge_reports(gauge_dir)

    gauge_public_base = _compose_public_url(public_base_url, "gauge-specs")
    enhance_gauge_report(gauge_dir, public_base_url=gauge_public_base)
    placeholder_count, screenshot_reasons = _collect_screenshot_issues(gauge_dir)
    screenshot_notice = _format_screenshot_notice(placeholder_count, screenshot_reasons)
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
        output_dir=parsed.output,
        public_base_url=parsed.public_base_url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
