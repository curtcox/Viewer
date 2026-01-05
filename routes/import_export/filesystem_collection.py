"""Application source file collection and traversal."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from flask import current_app


# Template directories to include in exports
APP_SOURCE_TEMPLATE_DIRECTORIES: tuple[str, ...] = (
    "templates",
    "reference/templates",
)

# Static asset directories to include in exports
APP_SOURCE_STATIC_DIRECTORIES: tuple[str, ...] = ("static",)

# Other important application files to include
APP_SOURCE_OTHER_FILES: tuple[Path, ...] = (
    Path("pyproject.toml"),
    Path("requirements.txt"),
    Path("uv.lock"),
    Path(".env.sample"),
    Path("run"),
    Path("install"),
    Path("doctor"),
    Path("README.md"),
    Path("replit.md"),
)

# Python source exclusions
PYTHON_SOURCE_EXCLUDED_DIRS: set[str] = {
    "test",
    "tests",
    "__pycache__",
    "venv",
    ".venv",
}
PYTHON_SOURCE_EXCLUDED_FILENAMES: set[str] = {"run_coverage.py", "run_auth_tests.py"}

# Categories for organizing source files
APP_SOURCE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("python", "Python Source Files"),
    ("templates", "Templates"),
    ("static", "Static Files"),
    ("other", "Other App Files"),
)


def app_root_path() -> Path:
    """Return the application root directory path."""
    return Path(current_app.root_path)


def should_include_python_source(relative_path: Path) -> bool:
    """Determine if a Python file should be included in exports."""
    if relative_path.suffix != ".py":
        return False

    if any(part in PYTHON_SOURCE_EXCLUDED_DIRS for part in relative_path.parts):
        return False

    if relative_path.name.startswith("test_"):
        return False

    if relative_path.name in PYTHON_SOURCE_EXCLUDED_FILENAMES:
        return False

    return True


def gather_python_source_paths() -> list[Path]:
    """Collect all Python source files to include in exports."""
    base_path = app_root_path()
    python_files: list[Path] = []

    for path in base_path.rglob("*.py"):
        try:
            relative_path = path.relative_to(base_path)
        except ValueError:
            continue

        if should_include_python_source(relative_path):
            python_files.append(relative_path)

    python_files.sort(key=lambda item: item.as_posix())
    return python_files


def gather_files_from_directories(relative_directories: Iterable[str]) -> list[Path]:
    """Collect files from specified directories relative to app root."""
    base_path = app_root_path()
    collected: list[Path] = []

    for relative in relative_directories:
        directory_path = base_path / relative
        if not directory_path.exists() or not directory_path.is_dir():
            continue

        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                collected.append(file_path.relative_to(base_path))

    collected.sort(key=lambda item: item.as_posix())
    return collected


def gather_template_paths() -> list[Path]:
    """Collect all template files from template directories."""
    return gather_files_from_directories(APP_SOURCE_TEMPLATE_DIRECTORIES)


def gather_static_paths() -> list[Path]:
    """Collect all static asset files from static directories."""
    return gather_files_from_directories(APP_SOURCE_STATIC_DIRECTORIES)


def gather_other_app_files() -> list[Path]:
    """Collect other important application files like config and docs."""
    base_path = app_root_path()
    other_files: list[Path] = []

    for relative in APP_SOURCE_OTHER_FILES:
        candidate = base_path / relative
        if candidate.exists() and candidate.is_file():
            other_files.append(relative)

    other_files.sort(key=lambda item: item.as_posix())
    return other_files


# Map of category keys to their collection functions
APP_SOURCE_COLLECTORS: dict[str, Callable[[], list[Path]]] = {
    "python": gather_python_source_paths,
    "templates": gather_template_paths,
    "static": gather_static_paths,
    "other": gather_other_app_files,
}
