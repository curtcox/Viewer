#!/usr/bin/env python3
"""Generate the Gauge specification summary used in CI."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


def parse_gauge_html_report(html_path: Path) -> dict[str, Any] | None:
    """Parse Gauge HTML report to extract execution summary."""
    if not html_path.exists():
        return None

    try:
        content = html_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Gauge HTML reports embed JSON data in a script tag
    # Look for patterns like: gauge.executionResult = {...}
    json_patterns = [
        r"gauge\.executionResult\s*=\s*({[^<]+});",
        r"var\s+executionResult\s*=\s*({[^<]+});",
        r"executionResult\s*=\s*({[^<]+});",
    ]

    for pattern in json_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                # Clean up the JSON string (remove trailing commas, etc.)
                json_str = re.sub(r",\s*}", "}", json_str)
                json_str = re.sub(r",\s*]", "]", json_str)
                return json.loads(json_str)
            except (json.JSONDecodeError, AttributeError):
                continue

    return None


def parse_gauge_log(log_path: Path) -> dict[str, Any]:
    """Parse Gauge execution log to extract summary information."""
    result: dict[str, Any] = {
        "specs_run": [],
        "specs_failed": [],
        "missing_steps": [],
        "failed_scenarios": [],
        "total_scenarios": 0,
        "passed_scenarios": 0,
        "failed_scenarios_count": 0,
    }

    if not log_path.exists():
        return result

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    lines = content.splitlines()

    # Track current spec
    current_spec: str | None = None

    for line in lines:
        line = line.strip()

        # Extract spec file path (e.g., "specs/example.spec")
        spec_match = re.match(r"^([a-zA-Z0-9_/.-]+\.spec)\s*::", line)
        if spec_match:
            current_spec = spec_match.group(1)
            if current_spec not in result["specs_run"]:
                result["specs_run"].append(current_spec)

            # Check if scenario failed
            if "-> FAILED" in line or "✖" in line:
                scenario_match = re.search(r"::\s*(.+?)\s*(?:->|✖)", line)
                if scenario_match:
                    scenario_name = scenario_match.group(1).strip()
                    result["failed_scenarios"].append(
                        f"{current_spec} :: {scenario_name}"
                    )
                    result["specs_failed"].append(current_spec)
            elif "-> PASSED" in line or "✔" in line:
                pass

        # Detect missing steps (No step implementation matches)
        if re.search(
            r"no step implementation matches|No step implementation matches",
            line,
            re.IGNORECASE,
        ):
            step_match = re.search(r"matches:\s*(.+)$", line, re.IGNORECASE)
            if step_match:
                missing_step = step_match.group(1).strip()
                if missing_step not in result["missing_steps"]:
                    result["missing_steps"].append(missing_step)

        # Extract summary statistics
        if "Total scenarios:" in line:
            match = re.search(r"Total scenarios:\s*(\d+)", line)
            if match:
                result["total_scenarios"] = int(match.group(1))
        elif "Passed:" in line:
            match = re.search(r"Passed:\s*(\d+)", line)
            if match:
                result["passed_scenarios"] = int(match.group(1))
        elif "Failed:" in line:
            match = re.search(r"Failed:\s*(\d+)", line)
            if match:
                result["failed_scenarios_count"] = int(match.group(1))

    # Deduplicate specs lists
    result["specs_run"] = list(dict.fromkeys(result["specs_run"]))
    result["specs_failed"] = list(dict.fromkeys(result["specs_failed"]))

    return result


def _process_spec_failures(spec: dict, specs_run: list, specs_failed: list,
                          failed_scenarios: list) -> None:
    """Process a spec to extract failure information."""
    if not isinstance(spec, dict):
        return

    spec_name = spec.get("name", "")
    if not spec_name:
        return

    if spec_name not in specs_run:
        specs_run.append(spec_name)

    scenarios = spec.get("scenarios", [])
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        if scenario.get("executionStatus") != "FAILED":
            continue
        scenario_name = scenario.get("name", "")
        if not scenario_name:
            continue
        failed_scenarios.append(f"{spec_name} :: {scenario_name}")
        if spec_name not in specs_failed:
            specs_failed.append(spec_name)


def _extract_html_specs(html_data: dict, specs_run: list) -> None:
    """Extract spec names from HTML data specs section."""
    if "specs" not in html_data:
        return

    for spec in html_data["specs"]:
        if not isinstance(spec, dict):
            continue
        spec_name = spec.get("name", "")
        if spec_name and spec_name not in specs_run:
            specs_run.append(spec_name)


def _extract_execution_results(html_data: dict, specs_run: list, specs_failed: list,
                               failed_scenarios: list) -> None:
    """Extract execution results from HTML data."""
    exec_result = html_data.get("executionResult", {})
    if not isinstance(exec_result, dict):
        return

    if "specs" not in exec_result:
        return

    for spec in exec_result["specs"]:
        _process_spec_failures(spec, specs_run, specs_failed, failed_scenarios)


def build_summary(log_path: Path | None, html_report_path: Path | None) -> str:
    """Build markdown summary from Gauge execution results."""
    lines: list[str] = ["### Gauge specifications", ""]

    # Parse log file for summary info
    log_data = parse_gauge_log(log_path) if log_path else {}

    # Try to parse HTML report for additional info
    html_data = None
    if html_report_path:
        html_data = parse_gauge_html_report(html_report_path)

    # Extract information from parsed data
    specs_run = log_data.get("specs_run", [])
    specs_failed = log_data.get("specs_failed", [])
    missing_steps = log_data.get("missing_steps", [])
    failed_scenarios = log_data.get("failed_scenarios", [])
    total_scenarios = log_data.get("total_scenarios", 0)
    passed_scenarios = log_data.get("passed_scenarios", 0)
    failed_scenarios_count = log_data.get("failed_scenarios_count", 0)

    # If HTML report has data, use it to supplement
    if html_data and isinstance(html_data, dict):
        _extract_html_specs(html_data, specs_run)
        _extract_execution_results(html_data, specs_run, specs_failed, failed_scenarios)

    # Build summary
    if not specs_run:
        lines.append("⚠️ **No specifications were executed.**")
        lines.append("")
        return "\n".join(lines)

    # Summary statistics
    lines.append("**Summary:**")
    lines.append(f"- Total specifications: {len(specs_run)}")
    if total_scenarios > 0:
        lines.append(f"- Total scenarios: {total_scenarios}")
        lines.append(f"- Passed scenarios: {passed_scenarios}")
        lines.append(f"- Failed scenarios: {failed_scenarios_count}")
    lines.append("")

    # Did all specs run?
    lines.append(f"✅ **All {len(specs_run)} specification(s) ran:**")
    for spec in sorted(specs_run):
        lines.append(f"  - {spec}")
    lines.append("")

    # Were there failures?
    if specs_failed or failed_scenarios:
        failure_header = (
            f"❌ **Failures detected ({len(specs_failed)} specification(s), "
            f"{len(failed_scenarios)} scenario(s)):**"
        )
        lines.append(failure_header)
        for spec in sorted(set(specs_failed)):
            lines.append(f"  - {spec}")
        if failed_scenarios:
            lines.append("")
            lines.append("  Failed scenarios:")
            # Limit to first 10
            for scenario in failed_scenarios[:10]:
                lines.append(f"    - {scenario}")
            if len(failed_scenarios) > 10:
                lines.append(f"    ... and {len(failed_scenarios) - 10} more")
        lines.append("")
    else:
        lines.append("✅ **No failures detected.**")
        lines.append("")

    # Were there missing steps?
    if missing_steps:
        lines.append(f"⚠️ **Missing step implementations ({len(missing_steps)}):**")
        # Limit to first 10
        for step in missing_steps[:10]:
            lines.append(f"  - `{step}`")
        if len(missing_steps) > 10:
            lines.append(f"  ... and {len(missing_steps) - 10} more")
        lines.append("")
    else:
        lines.append("✅ **No missing step implementations.**")
        lines.append("")

    # Add link to full report
    if html_report_path:
        lines.append(f"📄 Full report: `{html_report_path}`")
        lines.append("")

    return "\n".join(lines)


def write_summary(content: str, summary_path: Path | None) -> None:
    """Write summary to file or stdout."""
    if summary_path:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        print(content, end="")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
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
        "--summary",
        type=Path,
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help=(
            "File to append the summary to. Defaults to the "
            "GITHUB_STEP_SUMMARY output in CI."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    summary_content = build_summary(args.log, args.html_report)
    write_summary(summary_content, args.summary)


if __name__ == "__main__":
    main()
