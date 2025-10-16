"""Lightweight runner for the project's Gauge-style specs.

The real Gauge CLI is not available in the execution environment, which means
we can't rely on `gauge run` to verify the Markdown specs that describe the
desired behaviour of key routes.  This module provides a minimal interpreter
for the spec files we keep under ``specs/`` so that we can still exercise the
documented scenarios during development and in automated checks.

Usage examples::

    python run_specs.py                      # run every ``*.spec`` file
    python run_specs.py specs/source_browser.spec

The runner understands the step sentences currently used in the specs and
executes the corresponding Gauge step implementations from
``step_impl/source_steps.py``.  It exits with a non-zero status code if any
step fails, making it suitable for CI integration.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Iterable, Sequence

from step_impl import source_steps


@dataclass
class Scenario:
    """A parsed spec scenario with its ordered steps."""

    name: str
    steps: Sequence[str]


@dataclass
class StepDefinition:
    """Map a step sentence pattern to its implementation callable."""

    pattern: re.Pattern[str]
    action: Callable[..., None]


STEP_DEFINITIONS: Sequence[StepDefinition] = (
    StepDefinition(
        pattern=re.compile(r"When I request /source"),
        action=lambda: source_steps.when_i_request_source(),
    ),
    StepDefinition(
        pattern=re.compile(r"The response status should be 200"),
        action=lambda: source_steps.then_status_is_200(),
    ),
    StepDefinition(
        pattern=re.compile(r"The response should contain Source Browser"),
        action=lambda: source_steps.then_response_contains_source_browser(),
    ),
    StepDefinition(
        pattern=re.compile(r"When I request (.+) with screenshot mode enabled"),
        action=lambda path: source_steps.when_i_request_path_with_screenshot_mode(path),
    ),
    StepDefinition(
        pattern=re.compile(r"The CID screenshot response should include expected content"),
        action=lambda: source_steps.then_cid_screenshot_contains_expected_content(),
    ),
    StepDefinition(
        pattern=re.compile(r"The uploads screenshot response should include sample data"),
        action=lambda: source_steps.then_uploads_screenshot_contains_sample_data(),
    ),
    StepDefinition(
        pattern=re.compile(r"The server events screenshot response should include sample data"),
        action=lambda: source_steps.then_server_events_screenshot_contains_sample_data(),
    ),
)


class SpecExecutionError(RuntimeError):
    """Raised when the runner cannot execute a step or scenario."""


def discover_specs(paths: Iterable[str] | None) -> list[Path]:
    """Return the spec files that should be executed."""

    if paths:
        spec_paths = [Path(p) for p in paths]
    else:
        spec_paths = sorted(Path("specs").glob("*.spec"))

    missing = [str(p) for p in spec_paths if not p.is_file()]
    if missing:
        raise SpecExecutionError(f"Spec file(s) not found: {', '.join(missing)}")

    return spec_paths


def parse_spec(spec_path: Path) -> list[Scenario]:
    """Parse a Markdown spec file into executable scenarios."""

    scenarios: list[Scenario] = []
    current_name: str | None = None
    current_steps: list[str] = []

    for raw_line in spec_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue

        if line.startswith("## "):
            if current_name:
                scenarios.append(Scenario(name=current_name, steps=tuple(current_steps)))
                current_steps.clear()
            current_name = line[3:].strip()
            continue

        if line.startswith("* "):
            if current_name is None:
                raise SpecExecutionError(
                    f"Found step outside of a scenario in {spec_path}: {line!r}"
                )
            current_steps.append(line[2:].strip())
            continue

    if current_name:
        scenarios.append(Scenario(name=current_name, steps=tuple(current_steps)))

    return scenarios


def _match_step(step_text: str) -> tuple[StepDefinition, Sequence[str]]:
    """Find the matching step definition and captured arguments."""

    for definition in STEP_DEFINITIONS:
        match = definition.pattern.fullmatch(step_text)
        if match:
            return definition, match.groups()
    raise SpecExecutionError(f"No step implementation found for: {step_text}")


def run_scenario(scenario: Scenario) -> None:
    """Execute a single scenario, raising on failure."""

    print(f"  Scenario: {scenario.name}")
    source_steps.reset_scenario_store()

    for step_text in scenario.steps:
        definition, arguments = _match_step(step_text)
        print(f"    Step: {step_text}")
        definition.action(*arguments)


def run_spec_file(spec_path: Path) -> None:
    """Execute every scenario contained in ``spec_path``."""

    print(f"Spec: {spec_path}")
    scenarios = parse_spec(spec_path)
    if not scenarios:
        print("  (no scenarios found)")
        return

    for scenario in scenarios:
        run_scenario(scenario)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the command-line interface."""

    parser = argparse.ArgumentParser(description="Execute Gauge-style specs without the Gauge CLI")
    parser.add_argument("spec", nargs="*", help="Optional spec file(s) to run")
    args = parser.parse_args(argv)

    spec_paths = discover_specs(args.spec)
    if not spec_paths:
        print("No spec files found.")
        return 1

    source_steps.setup_suite()

    try:
        for spec_path in spec_paths:
            run_spec_file(spec_path)
    except Exception as exc:  # pragma: no cover - converted to exit code
        print(f"Spec execution failed: {exc}")
        return 1

    print("All specs passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
