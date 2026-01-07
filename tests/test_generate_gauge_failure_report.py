"""Tests for the Gauge failure report generation script."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_gauge_failure_report import (
    SpecFailure,
    generate_failure_report,
    merge_failures,
    parse_gauge_html_report,
    parse_gauge_log_failures,
)


@pytest.fixture
def sample_gauge_log(tmp_path: Path) -> Path:
    """Create a sample Gauge execution log for testing."""
    log_path = tmp_path / "gauge-execution.log"
    log_content = """Gauge Specification Execution Log
Started: 2026-01-07T15:00:00Z
Command: gauge run specs
================================================================================

specs/import_export.spec :: Users can transport functionality between sites -> FAILED
* Given an origin site with a server named "shared-tool" returning "Hello from origin"
* And I export servers and their CID map from the origin site
* When I import the exported data into a fresh destination site
Error Message: AssertionError: Server not found in destination site
Traceback (most recent call last):
  File "/step_impl/import_export_steps.py", line 45, in verify_server_exists
    assert server_name in servers, f"Server {server_name} not found"
AssertionError: Server not found in destination site

specs/settings.spec :: User can update settings -> PASSED

specs/profile.spec :: User profile is displayed -> SKIPPED

specs/authorization.spec :: Unauthorized access is blocked -> FAILED
Error: Permission denied
Traceback (most recent call last):
  File "/step_impl/authorization_steps.py", line 23, in check_access
    raise PermissionError("Permission denied")

Total scenarios: 4
Passed: 1
Failed: 2

================================================================================
Completed: 2026-01-07T15:05:00Z
Exit code: 1
"""
    log_path.write_text(log_content, encoding="utf-8")
    return log_path


def test_parse_gauge_log_failures_empty_log(tmp_path: Path):
    """Test parsing an empty log file."""
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("", encoding="utf-8")

    failures = parse_gauge_log_failures(empty_log)
    assert failures == []


def test_parse_gauge_log_failures_nonexistent_log(tmp_path: Path):
    """Test parsing a nonexistent log file."""
    nonexistent = tmp_path / "nonexistent.log"
    failures = parse_gauge_log_failures(nonexistent)
    assert failures == []


def test_parse_gauge_log_failures_with_failures_and_skips(sample_gauge_log: Path):
    """Test parsing a log with both failures and skipped scenarios."""
    failures = parse_gauge_log_failures(sample_gauge_log)

    assert len(failures) == 3

    # Check failed scenario 1
    failed1 = next(
        f
        for f in failures
        if f.scenario_name == "Users can transport functionality between sites"
    )
    assert failed1.spec_file == "specs/import_export.spec"
    assert failed1.status == "FAILED"
    assert "AssertionError" in failed1.error_message
    assert "Traceback" in failed1.stack_trace
    assert failed1.step_text.startswith("*")

    # Check failed scenario 2
    failed2 = next(
        f for f in failures if f.scenario_name == "Unauthorized access is blocked"
    )
    assert failed2.spec_file == "specs/authorization.spec"
    assert failed2.status == "FAILED"
    assert "Permission denied" in failed2.error_message

    # Check skipped scenario
    skipped = next(f for f in failures if f.scenario_name == "User profile is displayed")
    assert skipped.spec_file == "specs/profile.spec"
    assert skipped.status == "SKIPPED"
    assert skipped.error_message == ""
    assert skipped.stack_trace == ""


def test_parse_gauge_html_report_nonexistent(tmp_path: Path):
    """Test parsing a nonexistent HTML report."""
    nonexistent = tmp_path / "nonexistent.html"
    failures = parse_gauge_html_report(nonexistent)
    assert failures == []


def test_parse_gauge_html_report_invalid_html(tmp_path: Path):
    """Test parsing invalid HTML without JSON data."""
    html_path = tmp_path / "invalid.html"
    html_path.write_text(
        "<html><body>No gauge data here</body></html>", encoding="utf-8"
    )
    failures = parse_gauge_html_report(html_path)
    assert failures == []


def test_merge_failures_empty_lists():
    """Test merging empty failure lists."""
    result = merge_failures([], [])
    assert result == []


def test_merge_failures_deduplicates():
    """Test that merge removes duplicates."""
    failure1 = SpecFailure(
        spec_file="specs/test.spec",
        scenario_name="Test scenario",
        status="FAILED",
        error_message="Error from log",
    )
    failure2 = SpecFailure(
        spec_file="specs/test.spec",
        scenario_name="Test scenario",
        status="FAILED",
        error_message="Error from HTML",
        stack_trace="Stack from HTML",
    )

    result = merge_failures([failure1], [failure2])

    assert len(result) == 1
    # Should keep first error message but add stack trace from second
    assert result[0].error_message == "Error from log"
    assert result[0].stack_trace == "Stack from HTML"


def test_merge_failures_combines_info():
    """Test that merge combines information from both sources."""
    log_failure = SpecFailure(
        spec_file="specs/test.spec",
        scenario_name="Test scenario",
        status="FAILED",
        error_message="",
        step_text="* Step from log",
    )
    html_failure = SpecFailure(
        spec_file="specs/test.spec",
        scenario_name="Test scenario",
        status="FAILED",
        error_message="Error from HTML",
        stack_trace="Stack from HTML",
    )

    result = merge_failures([log_failure], [html_failure])

    assert len(result) == 1
    assert result[0].error_message == "Error from HTML"
    assert result[0].stack_trace == "Stack from HTML"
    assert result[0].step_text == "* Step from log"


def test_generate_failure_report_empty_failures(tmp_path: Path):
    """Test generating a report with no failures."""
    output_path = tmp_path / "report.md"
    generate_failure_report([], output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "No failures or skipped scenarios detected" in content
    assert "Generated:" in content


def test_generate_failure_report_with_failures(tmp_path: Path):
    """Test generating a report with failures and skips."""
    failures = [
        SpecFailure(
            spec_file="specs/test1.spec",
            scenario_name="Failed scenario",
            status="FAILED",
            error_message="Something went wrong",
            stack_trace="File line 123\n  error here",
            step_text="* When something fails",
        ),
        SpecFailure(
            spec_file="specs/test2.spec",
            scenario_name="Skipped scenario",
            status="SKIPPED",
        ),
    ]

    output_path = tmp_path / "report.md"
    generate_failure_report(failures, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")

    # Check header and summary
    assert "Gauge Specification Failures and Skips Report" in content
    assert "Total Issues:** 2" in content
    assert "Failed Scenarios:** 1" in content
    assert "Skipped Scenarios:** 1" in content

    # Check failed scenario details
    assert "## Failed Scenarios" in content
    assert "Failed scenario" in content
    assert "specs/test1.spec" in content
    assert "❌ FAILED" in content
    assert "Something went wrong" in content
    assert "File line 123" in content
    assert "* When something fails" in content

    # Check skipped scenario details
    assert "## Skipped Scenarios" in content
    assert "Skipped scenario" in content
    assert "specs/test2.spec" in content
    assert "⚠️ SKIPPED" in content

    # Check investigation tips
    assert "Investigation Tips" in content
    assert "Review the spec file" in content


def test_generate_failure_report_creates_parent_dirs(tmp_path: Path):
    """Test that the report generation creates parent directories."""
    output_path = tmp_path / "nested" / "dir" / "report.md"

    failures = [
        SpecFailure(
            spec_file="specs/test.spec",
            scenario_name="Test",
            status="FAILED",
        )
    ]

    generate_failure_report(failures, output_path)

    assert output_path.exists()
    assert output_path.parent.exists()


def test_spec_failure_initialization():
    """Test SpecFailure class initialization."""
    failure = SpecFailure(
        spec_file="specs/example.spec",
        scenario_name="Example scenario",
        status="FAILED",
        error_message="Error occurred",
        stack_trace="Stack trace here",
        step_text="* Example step",
    )

    assert failure.spec_file == "specs/example.spec"
    assert failure.scenario_name == "Example scenario"
    assert failure.status == "FAILED"
    assert failure.error_message == "Error occurred"
    assert failure.stack_trace == "Stack trace here"
    assert failure.step_text == "* Example step"


def test_spec_failure_default_values():
    """Test SpecFailure with default parameter values."""
    failure = SpecFailure(
        spec_file="specs/example.spec",
        scenario_name="Example scenario",
        status="SKIPPED",
    )

    assert failure.spec_file == "specs/example.spec"
    assert failure.scenario_name == "Example scenario"
    assert failure.status == "SKIPPED"
    assert failure.error_message == ""
    assert failure.stack_trace == ""
    assert failure.step_text == ""
