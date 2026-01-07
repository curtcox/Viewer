#!/usr/bin/env python3
"""Generate a comprehensive failure and skip report for Gauge specifications.

This script parses Gauge execution logs and HTML reports to create a detailed
single-file report of all failed and skipped specs, including all information
needed to investigate, understand, and fix issues.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SpecFailure:
    """Represents a failed or skipped scenario in a Gauge spec."""

    def __init__(
        self,
        spec_file: str,
        scenario_name: str,
        status: str,
        error_message: str = "",
        stack_trace: str = "",
        step_text: str = "",
    ):
        self.spec_file = spec_file
        self.scenario_name = scenario_name
        self.status = status  # FAILED or SKIPPED
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.step_text = step_text


def parse_gauge_log_failures(log_path: Path) -> list[SpecFailure]:
    """Parse Gauge execution log to extract detailed failure information."""
    failures: list[SpecFailure] = []

    if not log_path.exists():
        return failures

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return failures

    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()

        # Extract spec file path (e.g., "specs/example.spec :: scenario name -> STATUS")
        spec_match = re.match(
            r"^([a-zA-Z0-9_/.-]+\.spec)\s*::\s*(.+?)\s*->\s*(FAILED|SKIPPED|PASSED)",
            line_stripped
        )

        if spec_match:
            spec_file = spec_match.group(1)
            scenario_name = spec_match.group(2).strip()
            status = spec_match.group(3)

            if status in ("FAILED", "SKIPPED"):
                # Collect error information for failed scenarios
                error_lines: list[str] = []
                stack_lines: list[str] = []
                step_text = ""

                # Advance to next line and collect error details
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()

                    # Stop if we hit another spec/scenario or summary
                    if (
                        next_line.endswith(".spec")
                        or (" :: " in next_line and "->" in next_line)
                        or next_line.startswith("Total scenarios:")
                        or next_line.startswith("Summary:")
                        or re.match(r"^={10,}", next_line)
                    ):
                        break

                    # Collect step text
                    if next_line.startswith("*") and not step_text:
                        step_text = next_line

                    # Collect error messages
                    if any(
                        pattern in next_line
                        for pattern in [
                            "Error Message:",
                            "AssertionError:",
                            "Exception:",
                            "Error:",
                        ]
                    ):
                        error_lines.append(next_line)

                    # Collect stack trace
                    if (
                        "Traceback" in next_line
                        or next_line.startswith("File ")
                        or (next_line.startswith("  ") and (error_lines or stack_lines))
                    ):
                        stack_lines.append(next_line)

                    i += 1

                # Save the failure
                failures.append(
                    SpecFailure(
                        spec_file=spec_file,
                        scenario_name=scenario_name,
                        status=status,
                        error_message="\n".join(error_lines),
                        stack_trace="\n".join(stack_lines),
                        step_text=step_text,
                    )
                )
                continue

        i += 1

    return failures


def parse_gauge_html_report(html_path: Path) -> list[SpecFailure]:
    """Parse Gauge HTML report to extract failure information."""
    failures: list[SpecFailure] = []

    if not html_path.exists():
        return failures

    try:
        content = html_path.read_text(encoding="utf-8")
    except OSError:
        return failures

    # Try to extract JSON data from HTML report
    json_patterns = [
        r"gauge\.executionResult\s*=\s*({[^<]+});",
        r"var\s+executionResult\s*=\s*({[^<]+});",
        r"executionResult\s*=\s*({[^<]+});",
    ]

    html_data: dict[str, Any] | None = None
    for pattern in json_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                json_str = re.sub(r",\s*}", "}", json_str)
                json_str = re.sub(r",\s*]", "]", json_str)
                html_data = json.loads(json_str)
                break
            except (json.JSONDecodeError, AttributeError):
                continue

    if not html_data:
        return failures

    # Extract execution results
    exec_result = html_data.get("executionResult", {})
    if not isinstance(exec_result, dict):
        return failures

    specs = exec_result.get("specs", [])
    for spec in specs:
        if not isinstance(spec, dict):
            continue

        spec_name = spec.get("name", "")
        scenarios = spec.get("scenarios", [])

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue

            scenario_name = scenario.get("name", "")
            status = scenario.get("executionStatus", "")

            if status in ("FAILED", "SKIPPED"):
                error_msg = ""
                stack_trace = ""
                step_text = ""

                # Extract error details from failed items
                if "items" in scenario:
                    for item in scenario["items"]:
                        if not isinstance(item, dict):
                            continue

                        if item.get("itemType") == "step":
                            step = item.get("step", {})
                            if step.get("result", {}).get("status") == "failed":
                                step_text = step.get("actualStepText", "")
                                error_msg = step.get("result", {}).get("errorMessage", "")
                                stack_trace = step.get("result", {}).get("stackTrace", "")

                failures.append(
                    SpecFailure(
                        spec_file=spec_name,
                        scenario_name=scenario_name,
                        status=status,
                        error_message=error_msg,
                        stack_trace=stack_trace,
                        step_text=step_text,
                    )
                )

    return failures


def merge_failures(
    log_failures: list[SpecFailure], html_failures: list[SpecFailure]
) -> list[SpecFailure]:
    """Merge failures from log and HTML, preferring more detailed information."""
    # Use dict to deduplicate by (spec_file, scenario_name)
    merged: dict[tuple[str, str], SpecFailure] = {}

    # Add all log failures first
    for failure in log_failures:
        key = (failure.spec_file, failure.scenario_name)
        merged[key] = failure

    # Merge in HTML failures, keeping more detailed info
    for failure in html_failures:
        key = (failure.spec_file, failure.scenario_name)
        if key in merged:
            # Merge information - prefer HTML error messages if log doesn't have them
            existing = merged[key]
            if not existing.error_message and failure.error_message:
                existing.error_message = failure.error_message
            if not existing.stack_trace and failure.stack_trace:
                existing.stack_trace = failure.stack_trace
            if not existing.step_text and failure.step_text:
                existing.step_text = failure.step_text
        else:
            merged[key] = failure

    return list(merged.values())


def generate_failure_report(
    failures: list[SpecFailure], output_path: Path
) -> None:
    """Generate a comprehensive failure report file."""
    # Ensure parent directories exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not failures:
        # Create empty report indicating no failures
        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Gauge Specification Failures and Skips Report\n\n")
            f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
            f.write("✅ **No failures or skipped scenarios detected.**\n")
        return

    # Categorize failures
    failed = [f for f in failures if f.status == "FAILED"]
    skipped = [f for f in failures if f.status == "SKIPPED"]

    with output_path.open("w", encoding="utf-8") as f:
        # Header
        f.write("# Gauge Specification Failures and Skips Report\n\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total Issues:** {len(failures)}\n")
        f.write(f"- **Failed Scenarios:** {len(failed)}\n")
        f.write(f"- **Skipped Scenarios:** {len(skipped)}\n\n")

        # Failed scenarios section
        if failed:
            f.write("## Failed Scenarios\n\n")
            f.write(
                f"The following {len(failed)} scenario(s) failed during execution. "
                "Each entry includes the spec file, scenario name, error details, "
                "and stack traces to help investigate and fix the issues.\n\n"
            )

            for i, failure in enumerate(failed, 1):
                f.write(f"### {i}. {failure.scenario_name}\n\n")
                f.write(f"**Spec File:** `{failure.spec_file}`\n\n")
                f.write(f"**Status:** ❌ FAILED\n\n")

                if failure.step_text:
                    f.write(f"**Failed Step:**\n```\n{failure.step_text}\n```\n\n")

                if failure.error_message:
                    f.write(f"**Error Message:**\n```\n{failure.error_message}\n```\n\n")

                if failure.stack_trace:
                    f.write(f"**Stack Trace:**\n```\n{failure.stack_trace}\n```\n\n")

                f.write("---\n\n")

        # Skipped scenarios section
        if skipped:
            f.write("## Skipped Scenarios\n\n")
            f.write(
                f"The following {len(skipped)} scenario(s) were skipped during execution.\n\n"
            )

            for i, failure in enumerate(skipped, 1):
                f.write(f"### {i}. {failure.scenario_name}\n\n")
                f.write(f"**Spec File:** `{failure.spec_file}`\n\n")
                f.write(f"**Status:** ⚠️ SKIPPED\n\n")
                f.write("---\n\n")

        # Investigation tips
        f.write("## Investigation Tips\n\n")
        f.write("1. **Review the spec file** to understand the test scenario intent\n")
        f.write(
            "2. **Check the step implementation** in `step_impl/` directory for the failed steps\n"
        )
        f.write("3. **Run the specific spec locally** using: `./test-gauge -- specs/<spec-file>.spec`\n")
        f.write(
            "4. **Review the full Gauge HTML report** at `reports/html-report/index.html` for interactive details\n"
        )
        f.write("5. **Check the Gauge execution log** for additional context\n\n")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--log",
        type=Path,
        help="Path to the Gauge execution log file.",
    )
    parser.add_argument(
        "--html-report",
        type=Path,
        help="Path to the Gauge HTML report index.html file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the failure report file.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Parse failures from both sources
    log_failures: list[SpecFailure] = []
    if args.log:
        log_failures = parse_gauge_log_failures(args.log)

    html_failures: list[SpecFailure] = []
    if args.html_report:
        html_failures = parse_gauge_html_report(args.html_report)

    # Merge failures from both sources
    all_failures = merge_failures(log_failures, html_failures)

    # Sort by spec file and scenario name for consistent output
    all_failures.sort(key=lambda f: (f.spec_file, f.scenario_name))

    # Generate the report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_failure_report(all_failures, args.output)

    # Print summary to console
    failed_count = len([f for f in all_failures if f.status == "FAILED"])
    skipped_count = len([f for f in all_failures if f.status == "SKIPPED"])

    if all_failures:
        print(f"Generated failure report: {args.output}")
        print(f"  - Failed scenarios: {failed_count}")
        print(f"  - Skipped scenarios: {skipped_count}")
    else:
        print(f"No failures or skipped scenarios. Report: {args.output}")


if __name__ == "__main__":
    main()
