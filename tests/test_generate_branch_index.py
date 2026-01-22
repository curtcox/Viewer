"""Tests for the generate_branch_index.py script."""

import importlib.util
import json
import sys
from pathlib import Path


def _load_branch_index_module():
    """Load the generate_branch_index module for testing."""
    module_name = "test_generate_branch_index"
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "generate_branch_index.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load generate_branch_index module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


branch_index = _load_branch_index_module()


def test_count_job_status():
    """Test counting jobs by status."""
    statuses = {
        "job1": "success",
        "job2": "success",
        "job3": "failure",
        "job4": "success",
    }
    assert branch_index.count_job_status(statuses, "success") == 3
    assert branch_index.count_job_status(statuses, "failure") == 1
    assert branch_index.count_job_status(statuses, "skipped") == 0


def test_format_branch_summary_no_status():
    """Test formatting branch summary when no status is available."""
    html = branch_index.format_branch_summary("Main", ".", None)
    assert "Main" in html
    assert "No status information available" in html


def test_format_branch_summary_all_success():
    """Test formatting branch summary with all jobs successful."""
    statuses = {
        "job1": "success",
        "job2": "success",
        "job3": "success",
    }
    html = branch_index.format_branch_summary("Main", ".", statuses)
    assert "Main" in html
    assert "3 out of 3 jobs successful" in html
    assert "✓" in html
    assert "success" in html


def test_format_branch_summary_with_failures():
    """Test formatting branch summary with some failures."""
    statuses = {
        "job1": "success",
        "job2": "failure",
        "job3": "success",
    }
    html = branch_index.format_branch_summary("Dev", "dev", statuses)
    assert "Dev" in html
    assert "2 out of 3 jobs successful" in html
    assert "✖" in html
    assert "failure" in html


def test_load_job_statuses_missing_file(tmp_path):
    """Test loading job statuses when file doesn't exist."""
    path = tmp_path / "missing.json"
    assert branch_index.load_job_statuses(path) is None
    assert branch_index.load_job_statuses(None) is None


def test_load_job_statuses_valid_file(tmp_path):
    """Test loading job statuses from a valid JSON file."""
    path = tmp_path / "statuses.json"
    statuses = {
        "job1": "success",
        "job2": "failure",
    }
    path.write_text(json.dumps(statuses), encoding="utf-8")
    
    loaded = branch_index.load_job_statuses(path)
    assert loaded == statuses


def test_load_job_statuses_invalid_json(tmp_path):
    """Test loading job statuses from invalid JSON."""
    path = tmp_path / "invalid.json"
    path.write_text("not valid json", encoding="utf-8")
    
    assert branch_index.load_job_statuses(path) is None


def test_generate_index_page_basic(tmp_path):
    """Test generating a basic index page."""
    output_path = tmp_path / "index.html"
    
    main_statuses = {"job1": "success"}
    dev_statuses = {"job1": "failure"}
    test_statuses = None
    
    branch_index.generate_index_page(
        output_path, main_statuses, dev_statuses, test_statuses
    )
    
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    
    # Check for required HTML elements
    assert "<!DOCTYPE html>" in content
    assert "SecureApp CI Reports" in content
    assert "Main Branch" in content
    assert "Dev Branch" in content
    assert "Test Branch" in content
    
    # Check for status summaries
    assert "1 out of 1 jobs successful" in content
    
    # Check for visual indicators
    assert "✓" in content or "✖" in content


def test_main_creates_index(tmp_path):
    """Test that main function creates an index file."""
    output_path = tmp_path / "test-index.html"
    
    # Create sample status files
    main_statuses_path = tmp_path / "main.json"
    main_statuses_path.write_text(
        json.dumps({"job1": "success", "job2": "success"}),
        encoding="utf-8"
    )
    
    dev_statuses_path = tmp_path / "dev.json"
    dev_statuses_path.write_text(
        json.dumps({"job1": "failure"}),
        encoding="utf-8"
    )
    
    result = branch_index.main([
        "--output", str(output_path),
        "--main-statuses", str(main_statuses_path),
        "--dev-statuses", str(dev_statuses_path),
    ])
    
    assert result == 0
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "2 out of 2 jobs successful" in content
    assert "0 out of 1 jobs successful" in content
