"""GitHub Pull Request integration for import/export functionality."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from github import Github, GithubException
from github.Repository import Repository
from github.PullRequest import PullRequest

from cid_core import is_literal_cid
from generate_boot_image import BootImageGenerator

LOGGER = logging.getLogger(__name__)

# Boot image file path in the repository
BOOT_IMAGE_PATH = "reference/templates/default.boot.json"


REFERENCE_TEMPLATES_DIR = Path("reference") / "templates"
CIDS_DIR = Path("cids")


def _safe_filename(value: str) -> str:
    cleaned = "".join(
        ch if (ch.isalnum() or ch in {"-", "_"}) else "_" for ch in value.strip()
    )
    return cleaned.strip("_") or "unnamed"


def _load_section_from_export(payload: dict[str, Any], section: str) -> Any:
    cid_values = payload.get("cid_values", {})
    cid = payload.get(section)
    if not isinstance(cid, str):
        return None
    if not isinstance(cid_values, dict):
        return None
    raw = cid_values.get(cid)
    if not isinstance(raw, str):
        return None
    return json.loads(raw)


def _ensure_cid_file(base_dir: Path, cid: str, content: bytes) -> None:
    if is_literal_cid(cid):
        return
    target_dir = base_dir / CIDS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    cid_path = target_dir / cid
    if cid_path.exists():
        return
    cid_path.write_bytes(content)


def _merge_named_entries(
    existing: list[dict[str, Any]], incoming: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    ordered: list[str] = []
    for entry in existing:
        name = entry.get("name")
        if isinstance(name, str) and name not in by_name:
            by_name[name] = dict(entry)
            ordered.append(name)
    for entry in incoming:
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        if name in by_name:
            merged = dict(by_name[name])
            merged.update(entry)
            by_name[name] = merged
        else:
            by_name[name] = dict(entry)
            ordered.append(name)
    return [by_name[name] for name in ordered if name in by_name]


def prepare_boot_image_update(
    *,
    export_json: str,
    base_dir: Path,
) -> dict[str, Any]:
    payload = json.loads(export_json)
    if not isinstance(payload, dict):
        raise GitHubPRError("Export payload must be a JSON object.")

    cid_values = payload.get("cid_values", {})
    if not isinstance(cid_values, dict):
        cid_values = {}

    aliases = _load_section_from_export(payload, "aliases") or []
    servers = _load_section_from_export(payload, "servers") or []
    variables = _load_section_from_export(payload, "variables") or []

    if (
        not isinstance(aliases, list)
        or not isinstance(servers, list)
        or not isinstance(variables, list)
    ):
        raise GitHubPRError("Export payload sections were not in the expected format.")

    ref_dir = base_dir / REFERENCE_TEMPLATES_DIR
    aliases_dir = ref_dir / "aliases"
    servers_dir = ref_dir / "servers" / "definitions"
    aliases_dir.mkdir(parents=True, exist_ok=True)
    servers_dir.mkdir(parents=True, exist_ok=True)

    changed_paths: set[str] = set()

    merged_alias_entries: list[dict[str, Any]] = []
    for entry in aliases:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        definition_cid = entry.get("definition_cid")
        enabled = entry.get("enabled", True)
        if not isinstance(name, str) or not isinstance(definition_cid, str):
            continue
        definition_text = cid_values.get(definition_cid)
        if not isinstance(definition_text, str):
            raise GitHubPRError(
                f'Missing CID content for alias "{name}" ({definition_cid}).',
                details={"missing_cid": definition_cid, "entity": name},
            )
        filename = f"{_safe_filename(name)}.txt"
        relative_path = REFERENCE_TEMPLATES_DIR / "aliases" / filename
        absolute_path = base_dir / relative_path
        absolute_path.write_text(definition_text, encoding="utf-8")
        changed_paths.add(str(relative_path.as_posix()))
        merged_alias_entries.append(
            {
                "name": name,
                "definition_cid": str(relative_path.as_posix()),
                "enabled": bool(enabled),
            }
        )

    merged_server_entries: list[dict[str, Any]] = []
    for entry in servers:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        definition_cid = entry.get("definition_cid")
        enabled = entry.get("enabled", True)
        if not isinstance(name, str) or not isinstance(definition_cid, str):
            continue
        definition_text = cid_values.get(definition_cid)
        if not isinstance(definition_text, str):
            raise GitHubPRError(
                f'Missing CID content for server "{name}" ({definition_cid}).',
                details={"missing_cid": definition_cid, "entity": name},
            )
        filename = f"{_safe_filename(name)}.py"
        relative_path = REFERENCE_TEMPLATES_DIR / "servers" / "definitions" / filename
        absolute_path = base_dir / relative_path
        absolute_path.write_text(definition_text, encoding="utf-8")
        changed_paths.add(str(relative_path.as_posix()))
        merged_server_entries.append(
            {
                "name": name,
                "definition_cid": str(relative_path.as_posix()),
                "enabled": bool(enabled),
            }
        )

    source_path = ref_dir / "default.boot.source.json"
    if source_path.exists():
        existing_data = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(existing_data, dict):
            existing_aliases = (
                existing_data.get("aliases")
                if isinstance(existing_data.get("aliases"), list)
                else []
            )
            existing_servers = (
                existing_data.get("servers")
                if isinstance(existing_data.get("servers"), list)
                else []
            )
            existing_variables = (
                existing_data.get("variables")
                if isinstance(existing_data.get("variables"), list)
                else []
            )

            existing_data["aliases"] = _merge_named_entries(
                existing_aliases, merged_alias_entries
            )
            existing_data["servers"] = _merge_named_entries(
                existing_servers, merged_server_entries
            )

            incoming_variables: list[dict[str, Any]] = []
            for var in variables:
                if not isinstance(var, dict):
                    continue
                var_name = var.get("name")
                if not isinstance(var_name, str):
                    continue
                if var_name in {"templates", "uis"}:
                    continue
                incoming_variables.append(
                    {
                        "name": var_name,
                        "definition": var.get("definition"),
                        "enabled": bool(var.get("enabled", True)),
                    }
                )

            existing_data["variables"] = _merge_named_entries(
                existing_variables, incoming_variables
            )

            source_path.write_text(
                json.dumps(existing_data, indent=2), encoding="utf-8"
            )
            changed_paths.add(str(source_path.relative_to(base_dir).as_posix()))

    for cid, value in cid_values.items():
        if not isinstance(cid, str) or not isinstance(value, str):
            continue
        _ensure_cid_file(base_dir, cid, value.encode("utf-8"))
        if not is_literal_cid(cid):
            changed_paths.add(str((CIDS_DIR / cid).as_posix()))

    generator = BootImageGenerator(base_dir)
    generator.generate()

    for rel in generator.processed_files:
        if rel.startswith("reference/templates/minimal.boot."):
            continue
        changed_paths.add(rel)

    for rel in (
        "reference/templates/templates.json",
        "reference/templates/uis.json",
        "reference/templates/default.boot.json",
        "reference/templates/boot.json",
        "reference/templates/default.boot.cid",
        "reference/templates/boot.cid",
    ):
        if (base_dir / rel).exists():
            changed_paths.add(rel)

    cids_path = base_dir / CIDS_DIR
    if cids_path.exists():
        for cid_file in cids_path.iterdir():
            if cid_file.is_file():
                changed_paths.add(str((CIDS_DIR / cid_file.name).as_posix()))

    return {
        "mode": "prepared",
        "changed_paths": sorted(changed_paths),
    }


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
        if parsed.hostname not in ("github.com", "www.github.com"):
            return None, None, None

        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 4 and parts[2] == "pull":
            owner = parts[0]
            repo = parts[1]
            try:
                pr_number = int(parts[3])
                return owner, repo, pr_number
            except (ValueError, IndexError):
                return None, None, None

        return None, None, None
    except Exception as e:
        LOGGER.warning("Failed to parse GitHub PR URL: %s", e)
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
                "status": e.status,
                "message": (
                    e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
                ),
                "owner": owner,
                "repo": repo,
            },
        ) from e


def create_export_pr(
    export_json: str,
    *,
    target_repo: Optional[str] = None,
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
    base_dir = Path(__file__).resolve().parents[2]

    preparation = prepare_boot_image_update(export_json=export_json, base_dir=base_dir)

    if (
        not target_repo
        or not target_repo.strip()
        or not github_token
        or not github_token.strip()
    ):
        return {
            "mode": "manual",
            "target_repo": (target_repo or "").strip(),
            "branch_name": (branch_name or "").strip(),
            "prepared_paths": preparation["changed_paths"],
        }

    parts = target_repo.strip().split("/")
    if len(parts) != 2:
        raise GitHubPRError(
            f"Invalid repository format: {target_repo}. Expected 'owner/repo'",
            details={"target_repo": target_repo, "error": "invalid_format"},
        )

    owner, repo = parts

    try:
        client = get_github_client(github_token)
        repository = get_repository(client, owner, repo)

        # Get default branch
        default_branch = repository.default_branch

        # Generate branch name if not provided
        if not branch_name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
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
                        "branch_name": branch_name,
                        "error": "branch_exists",
                        "suggestion": "Try again to auto-generate a new branch name",
                    },
                ) from e
            raise

        commit_message = f"Update boot image via Viewer export\n\n{pr_description or 'Exported definitions'}"

        for rel_path in preparation["changed_paths"]:
            abs_path = base_dir / rel_path
            if not abs_path.exists() or not abs_path.is_file():
                continue
            file_bytes = abs_path.read_bytes()
            try:
                existing = repository.get_contents(rel_path, ref=default_branch)
                repository.update_file(
                    rel_path,
                    commit_message,
                    file_bytes.decode("utf-8", errors="replace"),
                    existing.sha,
                    branch=branch_name,
                )
            except GithubException as e:
                if e.status == 404:
                    repository.create_file(
                        rel_path,
                        commit_message,
                        file_bytes.decode("utf-8", errors="replace"),
                        branch=branch_name,
                    )
                else:
                    raise

        # Create the pull request
        pr_title = pr_title or "Update boot image definitions via Viewer export"
        pr_body = (
            pr_description
            or "This PR updates the default boot image with exported definitions from Viewer."
        )
        pr_body += "\n\n---\nGenerated by Viewer import/export system"

        pull_request = repository.create_pull(
            title=pr_title, body=pr_body, head=branch_name, base=default_branch
        )

        return {
            "url": pull_request.url,
            "number": pull_request.number,
            "html_url": pull_request.html_url,
            "branch_name": branch_name,
            "target_repo": target_repo,
            "mode": "github",
        }

    except GitHubPRError:
        raise
    except GithubException as e:
        error_msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
        raise GitHubPRError(
            f"GitHub API error: {error_msg}",
            details={
                "status": e.status,
                "target_repo": target_repo,
                "error": "github_api_error",
            },
        ) from e
    except Exception as e:
        raise GitHubPRError(
            f"Unexpected error creating PR: {str(e)}",
            details={"target_repo": target_repo, "error": "unexpected_error"},
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
        return (
            None,
            f"Invalid GitHub PR URL: {pr_url}. Expected format: https://github.com/owner/repo/pull/123",
        )

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
                    "status": e.status,
                    "pr_number": pr_number,
                    "owner": owner,
                    "repo": repo,
                },
            ) from e

        files = list(pull_request.get_files())

        allowed_markers = {
            "reference/templates/default.boot.source.json",
            "reference/templates/minimal.boot.source.json",
            "reference/templates/boot.source.json",
            "reference/templates/default.boot.cid",
            "reference/templates/minimal.boot.cid",
            "reference/templates/boot.cid",
        }

        touches_boot_image = any(
            getattr(file, "filename", None) in allowed_markers
            or getattr(file, "filename", None) == BOOT_IMAGE_PATH
            for file in files
        )

        if not touches_boot_image:
            return None, (
                f"Pull request does not modify a supported boot image file. "
                f"This PR cannot be imported as it was not created by the Viewer export system. "
                f"Files modified: {', '.join([f.filename for f in files[:5]])}"
            )

        # Import-from-PR remains a legacy mechanism that expects the export JSON
        # stored at the default boot image path.
        try:
            file_content = repository.get_contents(
                BOOT_IMAGE_PATH, ref=pull_request.head.sha
            )
        except GithubException as e:
            if e.status == 404:
                return None, (
                    f"Pull request updated boot image inputs but did not include {BOOT_IMAGE_PATH}. "
                    "Importing from PR currently requires the legacy export JSON file to be present."
                )
            return None, (
                f"Failed to read boot image file from PR: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}"
            )

        if not hasattr(file_content, "decoded_content"):
            return None, "Failed to decode file content from PR"

        json_data = file_content.decoded_content.decode("utf-8")
        try:
            json.loads(json_data)
        except json.JSONDecodeError as exc:
            return None, f"Boot image file contains invalid JSON: {str(exc)}"
        return json_data, None

    except GitHubPRError as e:
        return None, f"{e.message}. Details: {e.details}"
    except GithubException as e:
        error_msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
        return None, f"GitHub API error: {error_msg}"
    except Exception as e:
        LOGGER.exception("Unexpected error fetching PR data")
        return None, f"Unexpected error: {str(e)}"


__all__ = [
    "GitHubPRError",
    "create_export_pr",
    "fetch_pr_export_data",
    "parse_github_pr_url",
]
