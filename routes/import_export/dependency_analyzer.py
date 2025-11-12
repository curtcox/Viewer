"""Project dependency detection and version collection."""
from __future__ import annotations

import platform
import re
import sys
import tomllib
from importlib import metadata
from typing import Any

from .filesystem_collection import app_root_path


REQUIREMENT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*')


def parse_dependency_name(raw_value: Any) -> str | None:
    """Extract a clean package name from a requirement specifier."""
    if not isinstance(raw_value, str):
        return None

    text = raw_value.strip()
    if not text or text.startswith('#'):
        return None

    for prefix in ('-e ', '--', 'git+', 'http://', 'https://'):
        if text.startswith(prefix):
            return None

    text = text.split(';', 1)[0].strip()
    bracket_index = text.find('[')
    if bracket_index != -1:
        text = text[:bracket_index]

    for separator in ('===', '==', '>=', '<=', '!=', '~=', '>', '<'):
        if separator in text:
            text = text.split(separator, 1)[0]
            break

    match = REQUIREMENT_NAME_PATTERN.match(text)
    if not match:
        return None

    return match.group(0).lower()


def _parse_pyproject_dependencies(pyproject_path: Any) -> set[str]:
    """Extract dependency names from pyproject.toml file."""
    dependency_names: set[str] = set()
    if not pyproject_path.exists():
        return dependency_names

    try:
        data = tomllib.loads(pyproject_path.read_text('utf-8'))
    except (OSError, tomllib.TOMLDecodeError):
        return dependency_names

    if not isinstance(data, dict):
        return dependency_names

    project_section = data.get('project')
    if not isinstance(project_section, dict):
        return dependency_names

    raw_dependencies = project_section.get('dependencies', [])
    if not isinstance(raw_dependencies, list):
        return dependency_names

    for entry in raw_dependencies:
        name = parse_dependency_name(entry)
        if name:
            dependency_names.add(name)

    return dependency_names


def collect_project_dependencies() -> set[str]:
    """Collect dependency names from pyproject.toml and requirements.txt."""
    base_path = app_root_path()
    dependency_names: set[str] = set()

    # Collect from pyproject.toml
    pyproject_path = base_path / 'pyproject.toml'
    dependency_names.update(_parse_pyproject_dependencies(pyproject_path))

    # Collect from requirements.txt
    requirements_path = base_path / 'requirements.txt'
    if requirements_path.exists():
        try:
            raw_requirements = requirements_path.read_text('utf-8').splitlines()
        except OSError:
            raw_requirements = []
        for entry in raw_requirements:
            name = parse_dependency_name(entry)
            if name:
                dependency_names.add(name)

    return dependency_names


def gather_dependency_versions() -> dict[str, dict[str, str]]:
    """Collect installed versions of project dependencies."""
    dependency_versions: dict[str, dict[str, str]] = {}

    for name in sorted(collect_project_dependencies(), key=lambda item: item.lower()):
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        dependency_versions[name] = {'version': version}

    return dependency_versions


def build_runtime_section() -> dict[str, Any]:
    """Build runtime environment section for exports."""
    return {
        'python': {
            'implementation': platform.python_implementation(),
            'version': platform.python_version(),
            'executable': sys.executable or '',
        },
        'dependencies': gather_dependency_versions(),
    }
