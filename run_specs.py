"""Lightweight runner for the project's Gauge-style specs.

The real Gauge CLI is not available in the execution environment, which means
we can't rely on `gauge run` to verify the Markdown specs that describe the
desired behaviour of key routes.  This module provides a minimal interpreter
for the spec files we keep under ``specs/`` so that we can still exercise the
documented scenarios during development and in automated checks.

Usage examples::

    python run_specs.py                      # run every ``*.spec`` file
    python run_specs.py specs/source_browser.spec

The runner discovers the Gauge-style step implementations under
``step_impl/`` and executes them directly.  It exits with a non-zero status
code if any step fails, making it suitable for CI integration.
"""

from __future__ import annotations

import argparse
import sys
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Iterable, Sequence

from gauge_compat import (
    iter_before_scenario_hooks,
    iter_before_suite_hooks,
    iter_registered_steps,
)


def _load_step_modules(package: str = "step_impl") -> None:
    """Import all step implementation modules so decorators register hooks."""

    package_module = import_module(package)
    package_path = Path(package_module.__file__).resolve().parent

    for module_path in package_path.glob("*.py"):
        if module_path.name.startswith("_") or module_path.name == "__init__.py":
            continue
        module_name = f"{package}.{module_path.stem}"
        import_module(module_name)


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


STEP_DEFINITIONS: tuple[StepDefinition, ...] = ()
BEFORE_SUITE_HOOKS: tuple[Callable[..., None], ...] = ()
BEFORE_SCENARIO_HOOKS: tuple[Callable[..., None], ...] = ()

PLACEHOLDER_RE = re.compile(r"<([^>]+)>")


def _convert_gauge_pattern(pattern_text: str) -> re.Pattern[str]:
    """Translate a Gauge parameter pattern into a Python regular expression."""

    parts: list[str] = []
    last_index = 0
    for match in PLACEHOLDER_RE.finditer(pattern_text):
        parts.append(re.escape(pattern_text[last_index : match.start()]))
        parts.append("(.+)")
        last_index = match.end()

    parts.append(re.escape(pattern_text[last_index:]))
    regex = "^" + "".join(parts) + "$"
    return re.compile(regex)


def _initialise_runtime_state() -> None:
    """Load step definitions and lifecycle hooks from the step modules."""

    global STEP_DEFINITIONS, BEFORE_SUITE_HOOKS, BEFORE_SCENARIO_HOOKS

    _load_step_modules()

    step_definitions: list[StepDefinition] = []
    for pattern_text, action in iter_registered_steps():
        compiled = _convert_gauge_pattern(pattern_text)
        step_definitions.append(StepDefinition(pattern=compiled, action=action))

    if not step_definitions:
        raise SpecExecutionError("No Gauge step definitions registered.")

    STEP_DEFINITIONS = tuple(step_definitions)
    BEFORE_SUITE_HOOKS = tuple(iter_before_suite_hooks())
    BEFORE_SCENARIO_HOOKS = tuple(iter_before_scenario_hooks())


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

    if not STEP_DEFINITIONS:
        raise SpecExecutionError("Step definitions have not been initialised.")

    for definition in STEP_DEFINITIONS:
        match = definition.pattern.fullmatch(step_text)
        if match:
            return definition, match.groups()
    raise SpecExecutionError(f"No step implementation found for: {step_text}")


def run_scenario(scenario: Scenario) -> None:
    """Execute a single scenario, raising on failure."""

    print(f"  Scenario: {scenario.name}")

    for hook in BEFORE_SCENARIO_HOOKS:
        hook()

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

    _initialise_runtime_state()

    for hook in BEFORE_SUITE_HOOKS:
        hook()

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
