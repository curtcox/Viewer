"""Routes for browsing repository source files."""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Tuple

from flask import abort, current_app, render_template, send_file

from . import main_bp


@lru_cache(maxsize=4)
def _get_tracked_paths(root_path: str) -> frozenset[str]:
    """Return the git-tracked file paths relative to the repository root."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return frozenset()

    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return frozenset(files)


@lru_cache(maxsize=4)
def _get_all_project_files(root_path: str) -> frozenset[str]:
    """Return all project files for comprehensive source browsing."""
    root = Path(root_path)
    project_files = set()
    
    try:
        # Get all source files recursively, excluding common non-source directories
        exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules', '.tox'}
        
        for pattern in ["*.py", "*.html", "*.js", "*.css", "*.json", "*.md", "*.txt", "*.yml", "*.yaml", "*.toml", "*.ini", "*.cfg"]:
            for file_path in root.rglob(pattern):
                try:
                    # Skip files in excluded directories
                    if any(excluded in file_path.parts for excluded in exclude_dirs):
                        continue
                    
                    relative = file_path.relative_to(root).as_posix()
                    project_files.add(relative)
                except ValueError:
                    continue
    except Exception:
        pass
    
    return frozenset(project_files)


def _get_comprehensive_paths(root_path: str) -> frozenset[str]:
    """Get both git-tracked and all project files for comprehensive coverage."""
    tracked = _get_tracked_paths(root_path)
    all_files = _get_all_project_files(root_path)
    return tracked | all_files


def _build_breadcrumbs(path: str) -> List[Tuple[str, str]]:
    """Create breadcrumbs for the requested path."""
    breadcrumbs: List[Tuple[str, str]] = [("", "Source")]
    if not path:
        return breadcrumbs

    parts = path.split("/")
    for index in range(len(parts)):
        crumb_path = "/".join(parts[: index + 1])
        breadcrumbs.append((crumb_path, parts[index]))
    return breadcrumbs


def _directory_listing(path: str, tracked_paths: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Return immediate subdirectories and files for a directory path."""
    prefix = f"{path}/" if path else ""
    directories: set[str] = set()
    files: List[str] = []

    for tracked in tracked_paths:
        if prefix and not tracked.startswith(prefix):
            continue

        remainder = tracked[len(prefix) :] if prefix else tracked
        if not remainder:
            continue

        if "/" in remainder:
            directories.add(remainder.split("/", 1)[0])
        else:
            files.append(remainder)

    return sorted(directories), sorted(files)


def _render_directory(path: str, tracked_paths: frozenset[str]):
    """Render the directory listing template."""
    directories, files = _directory_listing(path, tracked_paths)
    breadcrumbs = _build_breadcrumbs(path)

    return render_template(
        "source_browser.html",
        breadcrumbs=breadcrumbs,
        current_path=path,
        directories=directories,
        files=files,
        file_content=None,
        is_file=False,
        path_prefix=f"{path}/" if path else "",
    )


def _render_file(path: str, root_path: Path):
    """Render a file from the repository, falling back to download for binary data."""
    repository_root = root_path.resolve()
    file_path = (repository_root / path).resolve()

    if not file_path.is_file() or repository_root not in file_path.parents:
        abort(404)

    try:
        file_content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return send_file(file_path)

    breadcrumbs = _build_breadcrumbs(path)

    return render_template(
        "source_browser.html",
        breadcrumbs=breadcrumbs,
        current_path=path,
        directories=[],
        files=[],
        file_content=file_content,
        is_file=True,
        path_prefix=f"{path}/" if path else "",
    )


def _is_tracked_directory(path: str, tracked_paths: frozenset[str]) -> bool:
    """Determine if the requested path corresponds to a tracked directory."""
    prefix = f"{path}/"
    return any(tracked.startswith(prefix) for tracked in tracked_paths)


@main_bp.route("/source", defaults={"requested_path": ""}, strict_slashes=False)
@main_bp.route("/source/<path:requested_path>")
def source_browser(requested_path: str):
    """Browse all project source files with comprehensive coverage."""
    # Get comprehensive paths (both git-tracked and all project files)
    comprehensive_paths = _get_comprehensive_paths(current_app.root_path)
    if not comprehensive_paths:
        # When no files are available, show an empty view.
        return _render_directory("", comprehensive_paths)

    normalized = requested_path.strip("/")
    if not normalized:
        return _render_directory("", comprehensive_paths)

    safe_path = Path(normalized)
    if safe_path.is_absolute() or ".." in safe_path.parts:
        abort(404)

    relative_path = safe_path.as_posix()
    repository_root = Path(current_app.root_path)

    if relative_path in comprehensive_paths:
        return _render_file(relative_path, repository_root)

    if _is_tracked_directory(relative_path, comprehensive_paths):
        return _render_directory(relative_path, comprehensive_paths)

    abort(404)
