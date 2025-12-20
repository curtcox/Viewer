#!/usr/bin/env python3
"""Run the project's automated tests with coverage reporting.

This script mirrors the configuration used in CI so developers can reproduce
coverage runs locally.  Any additional arguments are forwarded directly to
pytest.  For example::

    python run_coverage.py --xml --html
    python run_coverage.py -- --maxfail=1 -k auth
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent
HTML_REPORT_DIR = ROOT_DIR / "htmlcov"
COVERAGE_DATA_FILE = ROOT_DIR / ".coverage"
COVERAGE_XML_FILE = ROOT_DIR / "coverage.xml"

DEFAULT_ENV = {
    "DATABASE_URL": "sqlite:///:memory:",
    "SESSION_SECRET": "test-secret-key",
    "TESTING": "True",
}


def build_environment() -> dict[str, str]:
    """Return the execution environment for running the test suite."""

    env = os.environ.copy()
    python_path = env.get("PYTHONPATH")
    if python_path:
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT_DIR), python_path])
    else:
        env["PYTHONPATH"] = str(ROOT_DIR)

    for key, value in DEFAULT_ENV.items():
        env.setdefault(key, value)

    return env


def resolve_summary_path(path: Path) -> Path:
    """Return an absolute path for the requested summary file."""

    if not path.is_absolute():
        path = ROOT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def erase_previous_data(
    env: dict[str, str], *, clean_html: bool, clean_xml: bool
) -> None:
    """Remove previous coverage output so fresh reports are generated."""

    subprocess.run(
        [sys.executable, "-m", "coverage", "erase"],
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )

    if clean_html and HTML_REPORT_DIR.exists():
        shutil.rmtree(HTML_REPORT_DIR)

    if clean_xml and COVERAGE_XML_FILE.exists():
        COVERAGE_XML_FILE.unlink()


def run_coverage_report(
    env: dict[str, str], fail_under: Optional[float]
) -> tuple[str, int]:
    """Generate the textual coverage report and capture its output."""

    command = [sys.executable, "-m", "coverage", "report"]
    if fail_under is not None:
        command.extend(["--fail-under", str(fail_under)])

    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    return completed.stdout, completed.returncode


def generate_xml_report(env: dict[str, str]) -> int:
    """Create ``coverage.xml`` for consumption by other tools."""

    completed = subprocess.run(
        [sys.executable, "-m", "coverage", "xml"],
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )

    if completed.returncode == 0:
        print(f"XML coverage report written to {COVERAGE_XML_FILE}")

    return completed.returncode


def generate_html_report(env: dict[str, str]) -> int:
    """Create the HTML coverage report under ``htmlcov/``."""

    completed = subprocess.run(
        [sys.executable, "-m", "coverage", "html"],
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )

    if completed.returncode == 0:
        index_path = HTML_REPORT_DIR / "index.html"
        print(f"HTML coverage report available at {index_path}")

    return completed.returncode


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command-line arguments and normalise defaults."""

    parser = argparse.ArgumentParser(
        description="Run pytest with coverage enabled",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--html", action="store_true", help="Generate the HTML coverage report"
    )
    parser.add_argument(
        "--xml", action="store_true", help="Generate the XML coverage report"
    )
    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument(
        "--report",
        dest="report",
        action="store_true",
        help="Show the text coverage report",
    )
    report_group.add_argument(
        "--no-report",
        dest="report",
        action="store_false",
        help="Skip the text coverage report",
    )
    parser.set_defaults(report=True)
    parser.add_argument(
        "--all", action="store_true", help="Generate HTML, XML and text reports"
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        dest="fail_under",
        help="Fail if total coverage falls below the given percentage",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        dest="summary_file",
        help="Write the text coverage report to the specified file",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not erase existing coverage artefacts before running",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded to pytest (prefix with --)",
    )

    args = parser.parse_args(argv)

    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]

    if args.all:
        args.html = True
        args.xml = True
        args.report = True

    if args.summary_file is not None:
        args.report = True

    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for command-line execution."""

    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(list(argv))
    env = build_environment()

    if not args.no_clean:
        erase_previous_data(env, clean_html=args.html, clean_xml=args.xml)

    coverage_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "-m",
        "pytest",
        *args.pytest_args,
    ]
    tests_completed = subprocess.run(coverage_cmd, cwd=ROOT_DIR, env=env, check=False)
    exit_code = tests_completed.returncode

    if not COVERAGE_DATA_FILE.exists():
        print(
            "No coverage data was produced. Did the tests run successfully?",
            file=sys.stderr,
        )
        return exit_code or 1

    summary_output = ""
    if args.report:
        summary_output, report_returncode = run_coverage_report(env, args.fail_under)
        if args.summary_file is not None:
            summary_path = resolve_summary_path(args.summary_file)
            summary_path.write_text(summary_output)
        if exit_code == 0 and report_returncode != 0:
            exit_code = report_returncode

    if args.xml:
        xml_returncode = generate_xml_report(env)
        if exit_code == 0 and xml_returncode != 0:
            exit_code = xml_returncode

    if args.html:
        html_returncode = generate_html_report(env)
        if exit_code == 0 and html_returncode != 0:
            exit_code = html_returncode

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
