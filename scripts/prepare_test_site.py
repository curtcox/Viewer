#!/usr/bin/env python3
"""Utilities for assembling the GitHub Pages test-report site."""

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

from tests.gauge_report import enhance_gauge_report  # noqa: E402


def _move_contents(source: Path, destination: Path) -> None:
    """Move the contents of ``source`` into ``destination`` and delete ``source``."""

    if not source.exists():
        return

    destination.mkdir(parents=True, exist_ok=True)

    for entry in source.iterdir():
        target = destination / entry.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(entry), str(target))

    shutil.rmtree(source)


def _write_integration_index(integration_dir: Path, log_name: str, xml_name: str) -> None:
    log_path = integration_dir / log_name
    xml_path = integration_dir / xml_name
    index_path = integration_dir / "index.html"

    log_content = "No log output was captured."
    if log_path.exists():
        log_content = escape(log_path.read_text(encoding="utf-8", errors="replace"))

    xml_link = ""
    if xml_path.exists():
        xml_link = '<p><a href="{xml}">Download the JUnit XML report</a></p>'.format(xml=xml_name)

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


def _write_root_index(site_root: Path, unit_subdir: str, integration_subdir: str, gauge_subdir: str) -> None:
    index_path = site_root / "index.html"
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
    <li><a href="{unit}/index.html">Unit test coverage report</a></li>
    <li><a href="{integration}/index.html">Integration test results</a></li>
    <li><a href="{gauge}/index.html">Gauge HTML report</a></li>
  </ul>
</body>
</html>
""".format(unit=unit_subdir, integration=integration_subdir, gauge=gauge_subdir),
        encoding="utf-8",
    )


def prepare_site(
    *,
    site_root: Path,
    unit_subdir: str,
    gauge_subdir: str,
    integration_subdir: str,
    unit_html_subdir: str,
    gauge_reports_subdir: str,
    gauge_html_subdir: str,
    integration_log_name: str,
    integration_xml_name: str,
    gauge_artifacts_subdir: str,
) -> None:
    unit_dir = site_root / unit_subdir
    gauge_dir = site_root / gauge_subdir
    integration_dir = site_root / integration_subdir

    site_root.mkdir(parents=True, exist_ok=True)
    unit_dir.mkdir(parents=True, exist_ok=True)
    gauge_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)

    htmlcov_dir = unit_dir / unit_html_subdir
    if htmlcov_dir.is_dir():
        _move_contents(htmlcov_dir, unit_dir)

    gauge_html_dir = gauge_dir / gauge_reports_subdir / gauge_html_subdir
    if gauge_html_dir.is_dir():
        _move_contents(gauge_html_dir, gauge_dir)
        reports_dir = gauge_dir / gauge_reports_subdir
        if reports_dir.exists():
            shutil.rmtree(reports_dir)

    _write_integration_index(integration_dir, integration_log_name, integration_xml_name)

    if gauge_artifacts_subdir:
        enhance_gauge_report(gauge_dir, artifacts_subdir=gauge_artifacts_subdir)

    _write_root_index(site_root, unit_subdir, integration_subdir, gauge_subdir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the aggregated test report site.")
    parser.add_argument("--site-root", type=Path, default=Path("site"), help="Base directory that holds the site contents.")
    parser.add_argument("--unit-subdir", default="unit-tests", help="Subdirectory for unit test reports relative to the site root.")
    parser.add_argument("--gauge-subdir", default="gauge-specs", help="Subdirectory for Gauge reports relative to the site root.")
    parser.add_argument(
        "--integration-subdir",
        default="integration-tests",
        help="Subdirectory for integration test reports relative to the site root.",
    )
    parser.add_argument(
        "--unit-html-subdir",
        default="htmlcov",
        help="Subdirectory inside the unit reports that should be flattened into the unit directory.",
    )
    parser.add_argument(
        "--gauge-reports-subdir",
        default="reports",
        help="Subdirectory under the Gauge reports directory that may contain the HTML output.",
    )
    parser.add_argument(
        "--gauge-html-subdir",
        default="html-report",
        help="Name of the Gauge HTML report directory nested inside the reports subdirectory.",
    )
    parser.add_argument(
        "--gauge-artifacts-subdir",
        default="secureapp-artifacts",
        help="Directory under the Gauge report root that stores screenshot artifacts.",
    )
    parser.add_argument(
        "--integration-log-name",
        default="integration-tests.log",
        help="Log file to embed within the integration test index page.",
    )
    parser.add_argument(
        "--integration-xml-name",
        default="integration-tests-report.xml",
        help="JUnit XML file to link from the integration test index page.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prepare_site(
        site_root=args.site_root,
        unit_subdir=args.unit_subdir,
        gauge_subdir=args.gauge_subdir,
        integration_subdir=args.integration_subdir,
        unit_html_subdir=args.unit_html_subdir,
        gauge_reports_subdir=args.gauge_reports_subdir,
        gauge_html_subdir=args.gauge_html_subdir,
        integration_log_name=args.integration_log_name,
        integration_xml_name=args.integration_xml_name,
        gauge_artifacts_subdir=args.gauge_artifacts_subdir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
