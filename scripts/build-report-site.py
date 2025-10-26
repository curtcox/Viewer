#!/usr/bin/env python3
"""Build the static test report site from downloaded CI artifacts."""

from __future__ import annotations

import argparse
import shutil
import sys
from html import escape
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.gauge_report import enhance_gauge_report


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



def _write_landing_page(site_dir: Path) -> None:
    index_path = site_dir / "index.html"
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
  </style>
</head>
<body>
  <h1>SecureApp Test Reports</h1>
  <ul>
    <li><a href=\"unit-tests/index.html\">Unit test coverage report</a></li>
    <li><a href=\"integration-tests/index.html\">Integration test results</a></li>
    <li><a href=\"gauge-specs/index.html\">Gauge HTML report</a></li>
  </ul>
</body>
</html>
""",
        encoding="utf-8",
    )



def build_site(
    *,
    unit_tests_artifacts: Path | None,
    gauge_artifacts: Path | None,
    integration_artifacts: Path | None,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_tests_dir = output_dir / "unit-tests"
    gauge_dir = output_dir / "gauge-specs"
    integration_dir = output_dir / "integration-tests"

    _copy_artifacts(unit_tests_artifacts, unit_tests_dir)
    _copy_artifacts(gauge_artifacts, gauge_dir)
    _copy_artifacts(integration_artifacts, integration_dir)

    _flatten_htmlcov(unit_tests_dir)
    _flatten_gauge_reports(gauge_dir)

    enhance_gauge_report(gauge_dir)
    _build_integration_index(integration_dir)
    _write_landing_page(output_dir)



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
        output_dir=parsed.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
