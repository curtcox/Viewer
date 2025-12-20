import importlib.util
import json
import sys
from pathlib import Path


def _load_build_report_module():
    module_name = "test_build_report_site"
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build-report-site.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load build-report-site module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


build_report = _load_build_report_module()


def test_collect_screenshot_issues_counts_placeholders(tmp_path) -> None:
    gauge_dir = tmp_path / "gauge"
    artifacts_dir = gauge_dir / "secureapp-artifacts"
    artifacts_dir.mkdir(parents=True)

    (artifacts_dir / "one.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": False,
                    "placeholder": True,
                    "details": [
                        "pyppeteer is not installed.",
                        "Unable to read the shared placeholder image.",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    (artifacts_dir / "two.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": True,
                    "placeholder": False,
                    "details": "Response body is not HTML; browser screenshot skipped.",
                    "generated": "text-preview",
                }
            }
        ),
        encoding="utf-8",
    )

    # Captured screenshot should not be counted.
    (artifacts_dir / "three.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": True,
                    "placeholder": False,
                }
            }
        ),
        encoding="utf-8",
    )

    count, reasons = build_report._collect_screenshot_issues(gauge_dir)

    assert count == 1
    assert reasons == [
        "pyppeteer is not installed.",
        "Unable to read the shared placeholder image.",
    ]


def test_format_screenshot_notice_builds_section() -> None:
    notice = build_report._format_screenshot_notice(
        2, ["First reason", "Second reason"]
    )

    assert notice is not None
    assert "Gauge screenshot status" in notice
    assert "<li>First reason</li>" in notice
    assert "<li>Second reason</li>" in notice
    assert "gauge-specs/secureapp-artifacts" in notice
    assert "pyppeteer-install" in notice
    assert "libnss3" in notice


def test_write_landing_page_includes_notice(tmp_path) -> None:
    notice = '<section class="screenshot-status">Example</section>'
    build_report._write_landing_page(tmp_path, screenshot_notice=notice)

    index_path = tmp_path / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert notice in content


def test_parse_gauge_log_detects_status_prefixed_spec_lines(tmp_path) -> None:
    log_path = tmp_path / "gauge-execution.log"
    log_path.write_text(
        "\n".join(
            [
                "✓ specs/example.spec",
                "✗ specs/failed.spec :: Failing scenario -> FAILED",
                "Total scenarios: 2",
                "Passed: 1",
                "Failed: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_report._parse_gauge_log(log_path)

    assert "specs/example.spec" in summary.specs_run
    assert "specs/failed.spec" in summary.specs_run
    assert "specs/failed.spec" in summary.specs_failed
    assert summary.total_scenarios == 2
    assert summary.passed_scenarios == 1
    assert summary.failed_scenarios_count == 1


def test_build_linter_index_empty_summary(tmp_path) -> None:
    """Test that empty summary.txt shows 'No summary available' message."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create empty summary.txt
    (linter_dir / "summary.txt").write_text("", encoding="utf-8")
    (linter_dir / "output.txt").write_text("No issues found", encoding="utf-8")

    build_report._build_linter_index(linter_dir, "Pylint Report", "Pylint")

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert "No summary available." in content
    assert "<h2>Summary</h2><ul></ul>" not in content


def test_build_linter_index_whitespace_only_summary(tmp_path) -> None:
    """Test that summary.txt with only whitespace shows 'No summary available' message."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create summary.txt with only whitespace
    (linter_dir / "summary.txt").write_text("  \n  \n\t\n", encoding="utf-8")
    (linter_dir / "output.txt").write_text("No issues found", encoding="utf-8")

    build_report._build_linter_index(linter_dir, "Pylint Report", "Pylint")

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert "No summary available." in content
    assert "<h2>Summary</h2><ul></ul>" not in content


def test_build_linter_index_valid_summary(tmp_path) -> None:
    """Test that summary.txt with valid content is displayed correctly."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create summary.txt with valid content
    (linter_dir / "summary.txt").write_text(
        "Exit code: 1\nStatus: ✗ Issues found", encoding="utf-8"
    )
    (linter_dir / "output.txt").write_text("Some pylint errors", encoding="utf-8")

    build_report._build_linter_index(linter_dir, "Pylint Report", "Pylint")

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert "<h2>Summary</h2>" in content
    assert "Exit code: 1" in content
    assert "Status: ✗ Issues found" in content
    assert "No summary available." not in content


def test_build_linter_index_failure_no_artifacts(tmp_path) -> None:
    """Test that job failure without artifacts shows clear warning message."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # No summary.txt or output.txt files (simulating artifact download failure)
    # But job status is "failure"
    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="failure"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show warning message explaining the failure
    assert "⚠ Check Failed" in content
    assert "detailed results are not available" in content
    assert "The Pylint check failed" in content
    assert "Check the CI workflow logs for more details" in content
    # Should not show the output section when we have no data
    assert "<h2>Pylint output</h2>" not in content


def test_build_linter_index_failure_empty_artifacts(tmp_path) -> None:
    """Test that job failure with empty artifacts shows clear warning message."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create empty artifact files
    (linter_dir / "summary.txt").write_text("", encoding="utf-8")
    (linter_dir / "output.txt").write_text("", encoding="utf-8")

    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="failure"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show warning message
    assert "⚠ Check Failed" in content
    assert "detailed results are not available" in content


def test_build_linter_index_skipped(tmp_path) -> None:
    """Test that skipped job shows appropriate message."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="skipped"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show skipped message
    assert "The Pylint check was skipped" in content
    # Should not show the output section
    assert "<h2>Pylint output</h2>" not in content


def test_build_linter_index_failure_with_valid_artifacts(tmp_path) -> None:
    """Test that job failure with valid artifacts shows the actual errors (not warning)."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create valid artifact files with error content
    (linter_dir / "summary.txt").write_text(
        "Exit code: 8\nStatus: ✗ Issues found", encoding="utf-8"
    )
    (linter_dir / "output.txt").write_text(
        "some/file.py:10:5: E0001: Syntax error", encoding="utf-8"
    )

    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="failure"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show the actual summary and errors, NOT the warning
    assert "Exit code: 8" in content
    assert "Status: ✗ Issues found" in content
    assert "some/file.py:10:5: E0001: Syntax error" in content
    assert "⚠ Check Failed" not in content
    assert "detailed results are not available" not in content


def test_build_linter_index_success_no_artifacts(tmp_path) -> None:
    """Test that successful job without artifacts shows success message (backward compatible)."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # No artifacts, but job succeeded
    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="success"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show standard "no data" messages, not warnings
    assert "No summary available" in content
    assert "No output was captured" in content
    assert "⚠ Check Failed" not in content


def test_build_linter_index_failure_with_summary_but_empty_output(tmp_path) -> None:
    """Test that failure with summary but empty output shows neutral message, not success."""
    linter_dir = tmp_path / "pylint"
    linter_dir.mkdir(parents=True)

    # Create summary showing failure, but empty output.txt
    (linter_dir / "summary.txt").write_text(
        "Exit code: 2\nStatus: ✗ Issues found", encoding="utf-8"
    )
    (linter_dir / "output.txt").write_text("", encoding="utf-8")

    build_report._build_linter_index(
        linter_dir, "Pylint Report", "Pylint", job_status="failure"
    )

    index_path = linter_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should show the failure summary
    assert "Exit code: 2" in content
    assert "Status: ✗ Issues found" in content

    # Should NOT show success message (this is the regression test)
    assert "All checks passed - no issues found" not in content

    # Should show neutral "no output" message instead
    assert "No output was captured" in content

    # Should not show the warning for missing artifacts (we have summary)
    assert "⚠ Check Failed" not in content
    assert "detailed results are not available" not in content


def test_count_failing_jobs() -> None:
    """Test that _count_failing_jobs correctly counts failures."""
    # No failures
    assert build_report._count_failing_jobs({"job1": "success", "job2": "success"}) == 0
    # One failure
    assert build_report._count_failing_jobs({"job1": "success", "job2": "failure"}) == 1
    # Multiple failures
    assert (
        build_report._count_failing_jobs(
            {"job1": "failure", "job2": "failure", "job3": "success"}
        )
        == 2
    )
    # Skipped jobs don't count as failures
    assert build_report._count_failing_jobs({"job1": "skipped", "job2": "success"}) == 0
    # Empty dict
    assert build_report._count_failing_jobs({}) == 0


def test_get_background_color_all_pass() -> None:
    """Test that all passing jobs get light green background."""
    job_statuses = {"job1": "success", "job2": "success", "job3": "success"}
    assert build_report._get_background_color(job_statuses) == "#d4edda"


def test_get_background_color_one_failure() -> None:
    """Test that 1 failing job gets yellow background."""
    job_statuses = {"job1": "success", "job2": "failure"}
    assert build_report._get_background_color(job_statuses) == "#fff3cd"


def test_get_background_color_two_failures() -> None:
    """Test that 2 failing jobs get yellow background."""
    job_statuses = {"job1": "failure", "job2": "failure", "job3": "success"}
    assert build_report._get_background_color(job_statuses) == "#fff3cd"


def test_get_background_color_three_failures() -> None:
    """Test that 3 failing jobs get orange background."""
    job_statuses = {
        "job1": "failure",
        "job2": "failure",
        "job3": "failure",
        "job4": "success",
    }
    assert build_report._get_background_color(job_statuses) == "#ffe0b2"


def test_get_background_color_four_failures() -> None:
    """Test that 4 failing jobs get orange background."""
    job_statuses = {
        "job1": "failure",
        "job2": "failure",
        "job3": "failure",
        "job4": "failure",
    }
    assert build_report._get_background_color(job_statuses) == "#ffe0b2"


def test_get_background_color_five_failures() -> None:
    """Test that 5 failing jobs get red background."""
    job_statuses = {
        "job1": "failure",
        "job2": "failure",
        "job3": "failure",
        "job4": "failure",
        "job5": "failure",
    }
    assert build_report._get_background_color(job_statuses) == "#f8d7da"


def test_write_landing_page_applies_background_color(tmp_path) -> None:
    """Test that the landing page includes the correct background color."""
    # Test with all passing jobs
    job_statuses = {"job1": "success", "job2": "success"}
    build_report._write_landing_page(tmp_path, job_statuses=job_statuses)

    index_path = tmp_path / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Should have light green background
    assert "background-color: #d4edda" in content

    # Test with some failures
    job_statuses = {"job1": "failure", "job2": "failure", "job3": "failure"}
    build_report._write_landing_page(tmp_path, job_statuses=job_statuses)

    content = index_path.read_text(encoding="utf-8")

    # Should have orange background (3 failures)
    assert "background-color: #ffe0b2" in content
