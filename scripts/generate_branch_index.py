#!/usr/bin/env python3
"""Generate top-level index page with links to all branch reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def count_job_status(job_statuses: dict[str, str], status: str) -> int:
    """Count jobs with a specific status."""
    return sum(1 for s in job_statuses.values() if s == status)


def format_branch_summary(
    branch_name: str, branch_path: str, job_statuses: dict[str, str] | None
) -> str:
    """Format a branch summary with job status."""
    if not job_statuses:
        return f"""  <li class="branch-item">
    <div class="branch-info">
      <h3><a href="{branch_path}/">{branch_name}</a></h3>
      <p class="branch-status">No status information available</p>
    </div>
  </li>"""

    total_jobs = len(job_statuses)
    successful_jobs = count_job_status(job_statuses, "success")
    failed_jobs = count_job_status(job_statuses, "failure")
    
    # Determine status icon and class
    if failed_jobs == 0:
        status_icon = "✓"
        status_class = "success"
    else:
        status_icon = "✖"
        status_class = "failure"
    
    return f"""  <li class="branch-item {status_class}">
    <div class="branch-status-icon">{status_icon}</div>
    <div class="branch-info">
      <h3><a href="{branch_path}/">{branch_name}</a></h3>
      <p class="branch-status">{successful_jobs} out of {total_jobs} jobs successful</p>
    </div>
  </li>"""


def generate_index_page(
    output_path: Path,
    main_statuses: dict[str, str] | None,
    dev_statuses: dict[str, str] | None,
    test_statuses: dict[str, str] | None,
) -> None:
    """Generate the top-level index page."""
    main_html = format_branch_summary("Main Branch", ".", main_statuses)
    dev_html = format_branch_summary("Dev Branch", "dev", dev_statuses)
    test_html = format_branch_summary("Test Branch", "test", test_statuses)
    
    css = """    body { 
      font-family: system-ui, sans-serif; 
      margin: 2rem; 
      line-height: 1.6;
      max-width: 1200px;
      margin-left: auto;
      margin-right: auto;
    }
    h1 { 
      font-size: 2.5rem; 
      margin-bottom: 0.5rem;
      color: #24292e;
    }
    .subtitle {
      font-size: 1.1rem;
      color: #586069;
      margin-bottom: 2rem;
    }
    .branch-list {
      list-style: none;
      padding: 0;
      margin: 2rem 0;
    }
    .branch-item {
      display: flex;
      align-items: center;
      padding: 1.5rem;
      margin: 1rem 0;
      border: 2px solid #e1e4e8;
      border-radius: 8px;
      transition: all 0.2s ease;
    }
    .branch-item:hover {
      border-color: #0366d6;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .branch-item.success {
      background: #d4edda;
      border-color: #28a745;
    }
    .branch-item.failure {
      background: #f8d7da;
      border-color: #d73a49;
    }
    .branch-status-icon {
      flex-shrink: 0;
      font-size: 2rem;
      margin-right: 1.5rem;
      font-weight: bold;
    }
    .branch-item.success .branch-status-icon {
      color: #28a745;
    }
    .branch-item.failure .branch-status-icon {
      color: #d73a49;
    }
    .branch-info {
      flex-grow: 1;
    }
    .branch-info h3 {
      margin: 0 0 0.5rem 0;
      font-size: 1.5rem;
    }
    .branch-info h3 a {
      color: #0366d6;
      text-decoration: none;
    }
    .branch-info h3 a:hover {
      text-decoration: underline;
    }
    .branch-status {
      margin: 0;
      font-size: 1rem;
      color: #586069;
    }
    footer {
      margin-top: 3rem;
      padding-top: 2rem;
      border-top: 1px solid #e1e4e8;
      color: #586069;
      font-size: 0.9rem;
    }"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SecureApp CI Reports - All Branches</title>
  <style>
{css}
  </style>
</head>
<body>
  <h1>SecureApp CI Reports</h1>
  <p class="subtitle">Comprehensive test and quality reports across all active branches</p>
  
  <ul class="branch-list">
{main_html}
{dev_html}
{test_html}
  </ul>
  
  <footer>
    <p>Reports are automatically generated on every push to main, dev, and test branches.</p>
  </footer>
</body>
</html>"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def load_job_statuses(path: Path | None) -> dict[str, str] | None:
    """Load job statuses from JSON file."""
    if not path or not path.exists():
        return None
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        return None
    except (json.JSONDecodeError, OSError):
        return None


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate top-level index page with branch summaries"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for index.html"
    )
    parser.add_argument(
        "--main-statuses",
        type=Path,
        help="Path to main branch job-statuses.json"
    )
    parser.add_argument(
        "--dev-statuses",
        type=Path,
        help="Path to dev branch job-statuses.json"
    )
    parser.add_argument(
        "--test-statuses",
        type=Path,
        help="Path to test branch job-statuses.json"
    )
    
    args = parser.parse_args(argv)
    
    main_statuses = load_job_statuses(args.main_statuses)
    dev_statuses = load_job_statuses(args.dev_statuses)
    test_statuses = load_job_statuses(args.test_statuses)
    
    generate_index_page(args.output, main_statuses, dev_statuses, test_statuses)
    
    print(f"Generated top-level index at {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
