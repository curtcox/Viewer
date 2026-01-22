#!/usr/bin/env python3
"""Validate GitHub Pages deployment after site is published.

This script verifies that:
1. Branch-specific URLs exist (dev, test, main)
2. Index pages exist for each branch
3. Embedded git SHA matches the deployment SHA
4. All validations are logged with clear success/failure messages
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


@dataclass
class ValidationResult:
    """Result of a validation check."""

    name: str
    success: bool
    message: str


def fetch_url(url: str, max_retries: int = 3, retry_delay: int = 5) -> tuple[bool, str]:
    """Fetch URL content with retries.

    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        retry_delay: Delay in seconds between retries

    Returns:
        Tuple of (success, content or error message)
    """
    for attempt in range(max_retries):
        try:
            with urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8")
                return True, content
        except HTTPError as e:
            if e.code == 404:
                return False, f"404 Not Found: {url}"
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return False, f"HTTP Error {e.code}: {url}"
        except URLError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return False, f"URL Error: {e.reason}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return False, f"Unexpected error: {e}"
    return False, "Max retries exceeded"


def extract_git_sha(html_content: str) -> str | None:
    """Extract git SHA from HTML content.

    Args:
        html_content: HTML content to parse

    Returns:
        Git SHA if found, None otherwise
    """
    # Look for the hidden div with data-git-sha attribute
    pattern = r'<div\s+class="git-sha"\s+data-git-sha="([a-f0-9]{40})"\s+style="display:\s*none;">'
    match = re.search(pattern, html_content)
    if match:
        return match.group(1)
    return None


def validate_branch_url(base_url: str, branch_path: str, branch_name: str) -> ValidationResult:
    """Validate that a branch URL exists with an index page.

    Args:
        base_url: Base URL of the site
        branch_path: Path to the branch (empty for main, 'dev' or 'test' for others)
        branch_name: Name of the branch for display

    Returns:
        ValidationResult indicating success or failure
    """
    if branch_path:
        url = f"{base_url}/{branch_path}/"
    else:
        url = f"{base_url}/"

    success, content = fetch_url(url)

    if success:
        # Check if it looks like an index page
        if "SecureApp Test Reports" in content or "<h1>" in content:
            return ValidationResult(
                name=f"{branch_name} Branch URL",
                success=True,
                message=f"✓ {branch_name} branch index exists at {url}",
            )
        else:
            return ValidationResult(
                name=f"{branch_name} Branch URL",
                success=False,
                message=f"✗ {branch_name} branch URL exists but doesn't appear to be a valid index page: {url}",
            )
    else:
        return ValidationResult(
            name=f"{branch_name} Branch URL",
            success=False,
            message=f"✗ {branch_name} branch URL not accessible: {content}",
        )


def validate_git_sha(
    base_url: str, branch_path: str, branch_name: str, expected_sha: str
) -> ValidationResult:
    """Validate that the embedded git SHA matches the expected SHA.

    Args:
        base_url: Base URL of the site
        branch_path: Path to the branch (empty for main, 'dev' or 'test' for others)
        branch_name: Name of the branch for display
        expected_sha: Expected git SHA

    Returns:
        ValidationResult indicating success or failure
    """
    if branch_path:
        url = f"{base_url}/{branch_path}/"
    else:
        url = f"{base_url}/"

    success, content = fetch_url(url)

    if not success:
        return ValidationResult(
            name=f"{branch_name} Branch SHA",
            success=False,
            message=f"✗ Could not fetch {branch_name} branch for SHA validation: {content}",
        )

    embedded_sha = extract_git_sha(content)

    if embedded_sha is None:
        return ValidationResult(
            name=f"{branch_name} Branch SHA",
            success=False,
            message=f"✗ No git SHA found in {branch_name} branch index at {url}",
        )

    if embedded_sha == expected_sha:
        return ValidationResult(
            name=f"{branch_name} Branch SHA",
            success=True,
            message=f"✓ {branch_name} branch SHA matches deployment SHA: {expected_sha}",
        )
    else:
        return ValidationResult(
            name=f"{branch_name} Branch SHA",
            success=False,
            message=f"✗ {branch_name} branch SHA mismatch: expected {expected_sha}, found {embedded_sha}",
        )


def validate_deployment(
    base_url: str,
    branch: str,
    git_sha: str,
    validate_all_branches: bool = False,
) -> list[ValidationResult]:
    """Validate the GitHub Pages deployment.

    Args:
        base_url: Base URL of the GitHub Pages site
        branch: Branch that was just deployed ('main', 'dev', or 'test')
        git_sha: Git SHA that was just deployed
        validate_all_branches: Whether to validate all branches or just the deployed one

    Returns:
        List of ValidationResult objects
    """
    results: list[ValidationResult] = []

    # Determine which branch path to use
    branch_path = "" if branch == "main" else branch

    # Always validate the branch that was just deployed
    results.append(validate_branch_url(base_url, branch_path, branch.capitalize()))
    results.append(validate_git_sha(base_url, branch_path, branch.capitalize(), git_sha))

    # Optionally validate other branches (without SHA validation)
    if validate_all_branches:
        for other_branch in ["main", "dev", "test"]:
            if other_branch != branch:
                other_path = "" if other_branch == "main" else other_branch
                results.append(
                    validate_branch_url(base_url, other_path, other_branch.capitalize())
                )

    return results


def print_results(results: list[ValidationResult]) -> None:
    """Print validation results in a clear format.

    Args:
        results: List of validation results to print
    """
    print("\n" + "=" * 80)
    print("GitHub Pages Deployment Validation Results")
    print("=" * 80 + "\n")

    for result in results:
        print(result.message)

    print("\n" + "=" * 80)

    success_count = sum(1 for r in results if r.success)
    total_count = len(results)

    print(f"Summary: {success_count}/{total_count} checks passed")
    print("=" * 80 + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate GitHub Pages deployment after publishing"
    )
    parser.add_argument(
        "--base-url",
        default="https://curtcox.github.io/Viewer",
        help="Base URL of the GitHub Pages site",
    )
    parser.add_argument(
        "--branch",
        required=True,
        choices=["main", "dev", "test"],
        help="Branch that was just deployed",
    )
    parser.add_argument(
        "--git-sha",
        required=True,
        help="Git SHA that was just deployed",
    )
    parser.add_argument(
        "--validate-all-branches",
        action="store_true",
        help="Validate all branches, not just the one that was deployed",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=30,
        help="Seconds to wait before validation to allow GitHub Pages to update (default: 30)",
    )

    args = parser.parse_args(argv)

    # Wait for GitHub Pages to update
    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for GitHub Pages to update...")
        time.sleep(args.wait)

    # Run validation
    results = validate_deployment(
        args.base_url,
        args.branch,
        args.git_sha,
        args.validate_all_branches,
    )

    # Print results
    print_results(results)

    # Exit with error code if any checks failed
    if any(not r.success for r in results):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
