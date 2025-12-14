"""GitHub Pull Request integration for import/export functionality."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from github import Github, GithubException
from github.Repository import Repository
from github.PullRequest import PullRequest

LOGGER = logging.getLogger(__name__)

# Boot image file path in the repository
BOOT_IMAGE_PATH = "reference_templates/default.boot.json"


class GitHubPRError(Exception):
    """Error related to GitHub PR operations."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


def parse_github_pr_url(
    pr_url: str,
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Parse a GitHub PR URL to extract owner, repo, and PR number.

    Args:
        pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        Tuple of (owner, repo, pr_number) or (None, None, None) if invalid
    """
    try:
        parsed = urlparse(pr_url)
        if parsed.hostname not in ('github.com', 'www.github.com'):
            return None, None, None

        parts = parsed.path.strip('/').split('/')
        if len(parts) >= 4 and parts[2] == 'pull':
            owner = parts[0]
            repo = parts[1]
            try:
                pr_number = int(parts[3])
                return owner, repo, pr_number
            except (ValueError, IndexError):
                return None, None, None

        return None, None, None
    except Exception as e:
        LOGGER.warning(f"Failed to parse GitHub PR URL: {e}")
        return None, None, None


def get_github_client(token: Optional[str] = None) -> Github:
    """Get a GitHub API client.

    Args:
        token: Optional GitHub personal access token

    Returns:
        Github client instance
    """
    if token:
        return Github(token)
    return Github()  # Unauthenticated client with rate limits


def get_repository(client: Github, owner: str, repo: str) -> Repository:
    """Get a GitHub repository.

    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name

    Returns:
        Repository instance

    Raises:
        GitHubPRError: If repository cannot be accessed
    """
    try:
        repository = client.get_repo(f"{owner}/{repo}")
        return repository
    except GithubException as e:
        raise GitHubPRError(
            f"Failed to access repository {owner}/{repo}",
            details={
                'status': e.status,
                'message': (
                    e.data.get('message', str(e))
                    if hasattr(e, 'data')
                    else str(e)
                ),
                'owner': owner,
                'repo': repo,
            }
        ) from e


def create_export_pr(
    export_json: str,
    target_repo: str,
    github_token: Optional[str] = None,
    pr_title: Optional[str] = None,
    pr_description: Optional[str] = None,
    branch_name: Optional[str] = None,
) -> dict[str, Any]:
    """Create a GitHub PR with exported data.

    Args:
        export_json: JSON export data
        target_repo: Target repository in format "owner/repo"
        github_token: GitHub personal access token
        pr_title: Pull request title
        pr_description: Pull request description
        branch_name: Branch name for the PR (auto-generated if not provided)

    Returns:
        Dictionary with PR details including 'url', 'number', 'html_url'

    Raises:
        GitHubPRError: If PR creation fails
    """
    if not github_token:
        raise GitHubPRError(
            "GitHub token is required to create pull requests",
            details={'error': 'missing_token'}
        )

    # Parse target repository
    parts = target_repo.split('/')
    if len(parts) != 2:
        raise GitHubPRError(
            f"Invalid repository format: {target_repo}. Expected 'owner/repo'",
            details={'target_repo': target_repo, 'error': 'invalid_format'}
        )

    owner, repo = parts

    try:
        client = get_github_client(github_token)
        repository = get_repository(client, owner, repo)

        # Get default branch
        default_branch = repository.default_branch

        # Generate branch name if not provided
        if not branch_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            branch_name = f"viewer-export-{timestamp}"

        # Get the latest commit on the default branch
        base_ref = repository.get_git_ref(f"heads/{default_branch}")
        base_sha = base_ref.object.sha

        # Create a new branch
        try:
            repository.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                raise GitHubPRError(
                    f"Branch '{branch_name}' already exists",
                    details={
                        'branch_name': branch_name,
                        'error': 'branch_exists',
                        'suggestion': 'Try again to auto-generate a new branch name'
                    }
                ) from e
            raise

        # Get current file content if it exists
        try:
            file_content = repository.get_contents(BOOT_IMAGE_PATH, ref=default_branch)
            # Update the file
            commit_message = (
                f"Update boot image via Viewer export\n\n"
                f"{pr_description or 'Exported definitions'}"
            )
            repository.update_file(
                BOOT_IMAGE_PATH,
                commit_message,
                export_json,
                file_content.sha,
                branch=branch_name
            )
        except GithubException as e:
            if e.status == 404:
                # File doesn't exist, create it
                commit_message = (
                    f"Create boot image via Viewer export\n\n"
                    f"{pr_description or 'Exported definitions'}"
                )
                repository.create_file(
                    BOOT_IMAGE_PATH,
                    commit_message,
                    export_json,
                    branch=branch_name
                )
            else:
                raise

        # Create the pull request
        pr_title = (
            pr_title or "Update boot image definitions via Viewer export"
        )
        pr_body = (
            pr_description
            or "This PR updates the default boot image with "
            "exported definitions from Viewer."
        )
        pr_body += "\n\n---\nGenerated by Viewer import/export system"

        pull_request = repository.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch
        )

        return {
            'url': pull_request.url,
            'number': pull_request.number,
            'html_url': pull_request.html_url,
            'branch_name': branch_name,
            'target_repo': target_repo,
        }

    except GitHubPRError:
        raise
    except GithubException as e:
        error_msg = (
            e.data.get('message', str(e))
            if hasattr(e, 'data')
            else str(e)
        )
        raise GitHubPRError(
            f"GitHub API error: {error_msg}",
            details={
                'status': e.status,
                'target_repo': target_repo,
                'error': 'github_api_error',
            }
        ) from e
    except Exception as e:
        raise GitHubPRError(
            f"Unexpected error creating PR: {str(e)}",
            details={'target_repo': target_repo, 'error': 'unexpected_error'}
        ) from e


def fetch_pr_export_data(
    pr_url: str,
    github_token: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Fetch export data from a GitHub PR.

    Args:
        pr_url: GitHub PR URL
        github_token: Optional GitHub personal access token

    Returns:
        Tuple of (export_json, error_message)
        If successful, returns (json_string, None)
        If error, returns (None, error_message)
    """
    # Parse the PR URL
    owner, repo, pr_number = parse_github_pr_url(pr_url)
    if not owner or not repo or pr_number is None:
        return None, f"Invalid GitHub PR URL: {pr_url}. Expected format: https://github.com/owner/repo/pull/123"

    try:
        client = get_github_client(github_token)
        repository = get_repository(client, owner, repo)

        # Get the pull request
        try:
            pull_request: PullRequest = repository.get_pull(pr_number)
        except GithubException as e:
            if e.status == 404:
                return (
                    None,
                    f"Pull request #{pr_number} not found in {owner}/{repo}",
                )
            raise GitHubPRError(
                f"Failed to access pull request #{pr_number}",
                details={
                    'status': e.status,
                    'pr_number': pr_number,
                    'owner': owner,
                    'repo': repo,
                }
            ) from e

        # Get the files changed in the PR
        files = pull_request.get_files()
        boot_image_file = None

        for file in files:
            if file.filename == BOOT_IMAGE_PATH:
                boot_image_file = file
                break

        if not boot_image_file:
            files_modified = ', '.join([f.filename for f in files[:5]])
            return None, (
                f"Pull request does not modify the boot image file "
                f"({BOOT_IMAGE_PATH}). "
                f"This PR cannot be imported as it was not created by "
                f"the Viewer export system. "
                f"Files modified: {files_modified}"
            )

        # Get the file content from the PR branch
        try:
            file_content = repository.get_contents(
                BOOT_IMAGE_PATH, ref=pull_request.head.sha
            )
            if hasattr(file_content, 'decoded_content'):
                json_data = file_content.decoded_content.decode('utf-8')
                # Validate it's valid JSON
                try:
                    json.loads(json_data)
                    return json_data, None
                except json.JSONDecodeError as e:
                    return (
                        None,
                        f"Boot image file contains invalid JSON: {str(e)}",
                    )
            else:
                return None, "Failed to decode file content from PR"
        except GithubException as e:
            error_msg = (
                e.data.get('message', str(e))
                if hasattr(e, 'data')
                else str(e)
            )
            return None, f"Failed to read boot image file from PR: {error_msg}"

    except GitHubPRError as e:
        return None, f"{e.message}. Details: {e.details}"
    except GithubException as e:
        error_msg = (
            e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)
        )
        return None, f"GitHub API error: {error_msg}"
    except Exception as e:
        LOGGER.exception("Unexpected error fetching PR data")
        return None, f"Unexpected error: {str(e)}"


__all__ = [
    'GitHubPRError',
    'create_export_pr',
    'fetch_pr_export_data',
    'parse_github_pr_url',
]
