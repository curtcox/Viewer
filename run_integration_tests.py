#!/usr/bin/env python3
"""Run the integration test suite via pytest."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

from tests.test_support import ROOT_DIR, build_test_environment


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the integration test suite.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded to pytest (prefix with --).",
    )
    args = parser.parse_args(argv)
    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    return args


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(list(argv))
    env = build_test_environment()
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--override-ini",
        "addopts=",
        "-m",
        "integration",
        "tests/integration",
        *args.pytest_args,
    ]
    return subprocess.call(command, cwd=str(ROOT_DIR), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
