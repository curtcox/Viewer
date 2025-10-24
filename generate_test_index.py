#!/usr/bin/env python3
"""
Generate a markdown index of all tests in the project.

This script scans the codebase for:
- Unit tests (tests/test_*.py)
- Integration tests (tests/integration/test_*.py)
- Gauge specs (specs/*.spec)

It outputs a markdown file with links to each test definition.
"""

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TestInfo:
    """Information about a discovered test."""

    name: str
    file_path: str
    line_number: int
    test_type: str

    def to_markdown_link(self) -> str:
        """Generate a markdown link for this test."""
        return f"- [{self.name}]({self.file_path}:{self.line_number})"


class TestIndexer:
    """Indexes all tests in the project."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.tests: List[TestInfo] = []

    def find_unit_tests(self) -> None:
        """Find all unit tests in the tests/ directory."""
        tests_dir = self.root_dir / "tests"
        if not tests_dir.exists():
            return

        for test_file in tests_dir.glob("test_*.py"):
            # Skip integration tests
            if "integration" in test_file.parts:
                continue
            self._parse_python_test_file(test_file, "unit")

    def find_integration_tests(self) -> None:
        """Find all integration tests in tests/integration/."""
        integration_dir = self.root_dir / "tests" / "integration"
        if not integration_dir.exists():
            return

        for test_file in integration_dir.glob("test_*.py"):
            self._parse_python_test_file(test_file, "integration")

    def find_gauge_tests(self) -> None:
        """Find all Gauge specification scenarios."""
        specs_dir = self.root_dir / "specs"
        if not specs_dir.exists():
            return

        for spec_file in specs_dir.glob("*.spec"):
            self._parse_gauge_spec_file(spec_file)

    def _parse_python_test_file(self, file_path: Path, test_type: str) -> None:
        """Parse a Python test file to find test functions and methods."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return

        rel_path = file_path.relative_to(self.root_dir)

        # Find test functions (pytest style)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                self.tests.append(
                    TestInfo(
                        name=node.name,
                        file_path=str(rel_path),
                        line_number=node.lineno,
                        test_type=test_type,
                    )
                )

            # Find test methods in unittest.TestCase classes
            elif isinstance(node, ast.ClassDef):
                # Check if this is a test class
                is_test_class = (
                    node.name.startswith("Test")
                    or "TestCase" in [self._get_name(base) for base in node.bases]
                )

                if is_test_class:
                    for item in node.body:
                        if (
                            isinstance(item, ast.FunctionDef)
                            and item.name.startswith("test_")
                        ):
                            # Use class.method format for unittest tests
                            test_name = f"{node.name}.{item.name}"
                            self.tests.append(
                                TestInfo(
                                    name=test_name,
                                    file_path=str(rel_path),
                                    line_number=item.lineno,
                                    test_type=test_type,
                                )
                            )

    def _get_name(self, node: ast.AST) -> str:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def _parse_gauge_spec_file(self, file_path: Path) -> None:
        """Parse a Gauge spec file to find scenarios."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return

        rel_path = file_path.relative_to(self.root_dir)

        # Gauge scenarios start with ## (heading level 2)
        for line_num, line in enumerate(lines, start=1):
            # Match scenario headings (## Scenario Name)
            if line.strip().startswith("## "):
                scenario_name = line.strip()[3:].strip()
                self.tests.append(
                    TestInfo(
                        name=scenario_name,
                        file_path=str(rel_path),
                        line_number=line_num,
                        test_type="gauge",
                    )
                )

    def generate_markdown(self) -> str:
        """Generate markdown index of all tests."""
        # Sort tests by type and name
        unit_tests = sorted(
            [t for t in self.tests if t.test_type == "unit"], key=lambda t: t.name
        )
        integration_tests = sorted(
            [t for t in self.tests if t.test_type == "integration"],
            key=lambda t: t.name,
        )
        gauge_tests = sorted(
            [t for t in self.tests if t.test_type == "gauge"], key=lambda t: t.name
        )

        lines = [
            "# Test Index",
            "",
            "This index lists all tests in the project, organized by type.",
            "",
            f"**Total Tests:** {len(self.tests)}",
            f"- Unit Tests: {len(unit_tests)}",
            f"- Integration Tests: {len(integration_tests)}",
            f"- Gauge Tests: {len(gauge_tests)}",
            "",
        ]

        # Unit Tests section
        if unit_tests:
            lines.extend(
                [
                    "## Unit Tests",
                    "",
                    f"Total: {len(unit_tests)} tests",
                    "",
                ]
            )
            lines.extend([test.to_markdown_link() for test in unit_tests])
            lines.append("")

        # Integration Tests section
        if integration_tests:
            lines.extend(
                [
                    "## Integration Tests",
                    "",
                    f"Total: {len(integration_tests)} tests",
                    "",
                ]
            )
            lines.extend([test.to_markdown_link() for test in integration_tests])
            lines.append("")

        # Gauge Tests section
        if gauge_tests:
            lines.extend(
                [
                    "## Gauge Tests",
                    "",
                    f"Total: {len(gauge_tests)} scenarios",
                    "",
                ]
            )
            lines.extend([test.to_markdown_link() for test in gauge_tests])
            lines.append("")

        return "\n".join(lines)

    def run(self) -> str:
        """Run the indexer and return the markdown output."""
        print("Scanning for unit tests...")
        self.find_unit_tests()
        print(f"Found {len([t for t in self.tests if t.test_type == 'unit'])} unit tests")

        print("Scanning for integration tests...")
        self.find_integration_tests()
        print(
            f"Found {len([t for t in self.tests if t.test_type == 'integration'])} integration tests"
        )

        print("Scanning for Gauge tests...")
        self.find_gauge_tests()
        print(f"Found {len([t for t in self.tests if t.test_type == 'gauge'])} Gauge scenarios")

        print(f"\nTotal tests found: {len(self.tests)}")
        return self.generate_markdown()


def main():
    """Main entry point."""
    indexer = TestIndexer()
    markdown = indexer.run()

    output_file = "TEST_INDEX.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nTest index written to {output_file}")


if __name__ == "__main__":
    main()
