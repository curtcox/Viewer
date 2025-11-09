#!/usr/bin/env python3
"""Generate a markdown cross reference between site pages and automated checks."""

from __future__ import annotations

import argparse
import ast
import contextlib
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import coverage
import pytest

from tests.test_support import ROOT_DIR, build_test_environment


@dataclass
class RouteFunctionInfo:
    """Metadata about a Flask route function discovered via static analysis."""

    module_path: Path
    function_name: str
    start_line: int
    end_line: int
    route_paths: list[str] = field(default_factory=list)
    templates: set[str] = field(default_factory=set)
    tests_by_suite: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    specs: set[str] = field(default_factory=set)

    @property
    def identifier(self) -> str:
        return f"{self.module_path.as_posix()}::{self.function_name}"


RouteCollection = list[RouteFunctionInfo]


class TemplateCollector(ast.NodeVisitor):
    """Collect template names referenced in a function body."""

    TEMPLATE_FUNCTIONS = {
        "render_template",
        "render_template_string",
    }

    def __init__(self) -> None:
        self.templates: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 (ast API)
        func = node.func
        func_name = None
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr
        if func_name in self.TEMPLATE_FUNCTIONS and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self.templates.add(arg.value)
        self.generic_visit(node)


class FunctionCallCollector(ast.NodeVisitor):
    """Collect direct function calls made within a function body."""

    def __init__(self) -> None:
        self.called: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        if isinstance(func, ast.Name):
            self.called.add(func.id)
        self.generic_visit(node)


@dataclass
class FunctionDetails:
    node: ast.FunctionDef
    route_paths: list[str]
    templates: set[str]
    called_functions: set[str]


def _route_paths_from_decorators(decorator_list: Iterable[ast.expr]) -> list[str]:
    paths: list[str] = []
    for decorator in decorator_list:
        if isinstance(decorator, ast.Call):
            target = decorator.func
            attr = None
            if isinstance(target, ast.Attribute):
                attr = target.attr
            if attr not in {"route", "get", "post", "put", "patch", "delete"}:
                continue
            for arg in decorator.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    paths.append(arg.value)
            for keyword in decorator.keywords or []:
                if keyword.arg == "rule" and isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, str
                ):
                    paths.append(keyword.value.value)
    return paths


def _resolve_templates(
    function_name: str,
    functions: Mapping[str, FunctionDetails],
    seen: set[str],
) -> set[str]:
    if function_name in seen:
        return set()
    details = functions.get(function_name)
    if not details:
        return set()

    collected = set(details.templates)
    next_seen = seen | {function_name}
    for callee in details.called_functions:
        if callee in functions:
            collected.update(_resolve_templates(callee, functions, next_seen))
    return collected


def discover_route_functions(route_dir: Path) -> RouteCollection:
    """Return information about Flask route functions under ``route_dir``."""

    routes: RouteCollection = []
    for path in sorted(route_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        functions: dict[str, FunctionDetails] = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            route_paths = _route_paths_from_decorators(node.decorator_list)
            template_collector = TemplateCollector()
            template_collector.visit(node)
            call_collector = FunctionCallCollector()
            call_collector.visit(node)
            functions[node.name] = FunctionDetails(
                node=node,
                route_paths=route_paths,
                templates=template_collector.templates,
                called_functions={
                    callee for callee in call_collector.called if callee != node.name
                },
            )

        for details in functions.values():
            if not details.route_paths:
                continue
            templates = _resolve_templates(details.node.name, functions, set())
            routes.append(
                RouteFunctionInfo(
                    module_path=path.relative_to(ROOT_DIR),
                    function_name=details.node.name,
                    start_line=details.node.lineno,
                    end_line=details.node.end_lineno or details.node.lineno,
                    route_paths=details.route_paths,
                    templates=templates,
                )
            )
    return routes


def _apply_test_environment() -> contextlib.AbstractContextManager[None]:
    """Temporarily apply test environment variables expected by the suites."""

    env = build_test_environment()
    relevant_keys = {"PYTHONPATH", "DATABASE_URL", "SESSION_SECRET", "TESTING"}

    class _EnvGuard(contextlib.AbstractContextManager[None]):
        def __init__(self) -> None:
            self._original: dict[str, str | None] = {}

        def __enter__(self) -> None:
            self._original = {key: os.environ.get(key) for key in relevant_keys}
            for key in relevant_keys:
                if key in env:
                    os.environ[key] = env[key]
                elif key in os.environ:
                    del os.environ[key]

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            for key, value in self._original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return _EnvGuard()


def run_pytest_suite(name: str, pytest_args: list[str], data_file: Path) -> coverage.Coverage:
    """Execute ``pytest`` under coverage for the given suite and return loaded data."""

    print(f"[crossref] Running {name} suite with coverage...")
    cov = coverage.Coverage(config_file=str(ROOT_DIR / ".coveragerc"), data_file=str(data_file))
    cov.config.dynamic_context = "test_function"
    cov.erase()

    with _apply_test_environment():
        cov.start()
        try:
            result = pytest.main(pytest_args)
        finally:
            cov.stop()
            cov.save()
    if result != 0:
        raise RuntimeError(f"{name} suite failed with exit code {result}")

    cov.load()
    return cov


def gather_suite_coverage(reuse: bool) -> dict[str, coverage.Coverage]:
    """Run unit and integration suites, returning coverage objects keyed by suite."""

    coverage_dir = ROOT_DIR / ".coverage_crossref"
    coverage_dir.mkdir(exist_ok=True)

    suites = {
        "unit": {
            "pytest_args": [
                "--override-ini",
                'addopts=-m "not integration"',
                "-m",
                "not integration",
            ],
            "data_file": coverage_dir / "unit.coverage",
        },
        "integration": {
            "pytest_args": [
                "--override-ini",
                "addopts=",
                "-m",
                "integration",
                "tests/integration",
            ],
            "data_file": coverage_dir / "integration.coverage",
        },
    }

    collected: dict[str, coverage.Coverage] = {}
    for name, cfg in suites.items():
        data_file: Path = cfg["data_file"]
        if reuse and data_file.exists():
            cov = coverage.Coverage(data_file=str(data_file))
            cov.load()
            collected[name] = cov
            print(f"[crossref] Reused existing coverage data for {name} suite.")
            continue

        cov = run_pytest_suite(name, cfg["pytest_args"], data_file)
        collected[name] = cov
    return collected


def contexts_for_route(route: RouteFunctionInfo, cov: coverage.Coverage) -> set[str]:
    data = cov.get_data()
    absolute = str(ROOT_DIR / route.module_path)
    contexts_by_line = data.contexts_by_lineno(absolute)
    discovered: set[str] = set()
    for line in range(route.start_line, route.end_line + 1):
        for ctx in contexts_by_line.get(line, []):
            if ctx:
                discovered.add(ctx)
    return discovered


def format_context(context: str) -> str:
    module_name = context
    qual_parts: list[str] = []
    while module_name:
        candidate = ROOT_DIR / (module_name.replace(".", "/") + ".py")
        if candidate.exists():
            break
        module_name, sep, last = module_name.rpartition(".")
        if not sep:
            qual_parts.insert(0, last)
            module_name = ""
            break
        qual_parts.insert(0, last)
    if not module_name:
        module_name = context
        qual_parts = []
    display = module_name.replace(".", "/") + ".py"
    if qual_parts:
        display += "::" + "::".join(qual_parts)
    return display


def map_specs_by_route(spec_dir: Path) -> dict[str, set[str]]:
    pattern = re.compile(r"/[^\s\"]*")
    mapping: dict[str, set[str]] = defaultdict(set)
    for spec_file in sorted(spec_dir.glob("*.spec")):
        current_section = None
        for raw_line in spec_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                current_section = line[3:].strip()
                continue
            for match in pattern.findall(line):
                entry = f"{spec_file.name} — {current_section or 'Scenario'}"
                mapping[match].add(entry)
    return mapping


def aggregate_pages(routes: RouteCollection, spec_mapping: Mapping[str, set[str]]) -> dict[str, dict[str, object]]:
    pages: dict[str, dict[str, object]] = {}
    for route in routes:
        route_specs = set()
        for path in route.route_paths:
            route_specs.update(spec_mapping.get(path, set()))
        if route_specs:
            route.specs = route_specs
        for template in sorted(route.templates):
            entry = pages.setdefault(
                template,
                {
                    "routes": [],
                    "tests": defaultdict(set),
                    "specs": set(),
                },
            )
            entry["routes"].append(route)
            entry["specs"].update(route.specs)
            for suite, contexts in route.tests_by_suite.items():
                entry["tests"][suite].update(contexts)
    return pages


def generate_markdown(pages: Mapping[str, dict[str, object]]) -> str:
    lines = ["# Page Test Cross Reference", "", "This document maps site pages to the automated checks that exercise them.", ""]

    for template in sorted(pages):
        info = pages[template]
        routes: list[RouteFunctionInfo] = info["routes"]  # type: ignore[assignment]
        tests: Mapping[str, set[str]] = info["tests"]  # type: ignore[assignment]
        specs: set[str] = info["specs"]  # type: ignore[assignment]

        lines.append(f"## templates/{template}")
        lines.append("")

        lines.append("**Routes:**")
        for route in routes:
            route_desc = f"- `{route.identifier}`"
            if route.route_paths:
                route_desc += f" (paths: {', '.join(f'`{path}`' for path in route.route_paths)})"
            lines.append(route_desc)
        lines.append("")

        for suite_name in ("unit", "integration"):
            suite_tests = sorted(tests.get(suite_name, set()))
            label = "Unit tests" if suite_name == "unit" else "Integration tests"
            lines.append(f"**{label}:**")
            if suite_tests:
                for test in suite_tests:
                    lines.append(f"- `{test}`")
            else:
                lines.append("- _None_")
            lines.append("")

        lines.append("**Specs:**")
        if specs:
            for spec in sorted(specs):
                lines.append(f"- {spec}")
        else:
            lines.append("- _None_")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "docs" / "page_test_cross_reference.md",
        help="Path to write the generated markdown.",
    )
    parser.add_argument(
        "--reuse-coverage",
        action="store_true",
        help="Reuse coverage data from a previous run instead of executing the suites again.",
    )
    parser.add_argument(
        "--keep-coverage",
        action="store_true",
        help="Keep the intermediate coverage data files instead of deleting them.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    route_functions = discover_route_functions(ROOT_DIR / "routes")
    if not route_functions:
        print("[crossref] No route functions found under routes/; nothing to do.")
        return 0

    coverages = gather_suite_coverage(reuse=args.reuse_coverage)

    for suite_name, cov in coverages.items():
        for route in route_functions:
            contexts = {format_context(ctx) for ctx in contexts_for_route(route, cov)}
            if contexts:
                route.tests_by_suite.setdefault(suite_name, set()).update(contexts)

    spec_mapping = map_specs_by_route(ROOT_DIR / "specs")
    pages = aggregate_pages(route_functions, spec_mapping)

    output_path = args.output if args.output.is_absolute() else ROOT_DIR / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = generate_markdown(pages)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"[crossref] Wrote cross reference to {output_path.relative_to(ROOT_DIR)}")

    if not args.keep_coverage:
        for cov in coverages.values():
            data_file = Path(cov.config.data_file)
            with contextlib.suppress(FileNotFoundError):
                data_file.unlink()
        coverage_dir = ROOT_DIR / ".coverage_crossref"
        if coverage_dir.exists() and not any(coverage_dir.iterdir()):
            coverage_dir.rmdir()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
