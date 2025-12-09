"""Server templates package for the Viewer application.

This package contains predefined server templates that can be used to create new servers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable


def get_server_templates() -> list[dict[str, str]]:
    """Return copies of all available server templates.

    Returns:
        A list of template dictionaries, each containing 'id', 'name', 'description', and 'definition'.
    """
    return list(iter_server_templates())

def iter_server_templates() -> Iterable[Dict[str, Any]]:
    """Yield templates one-by-one without exposing internal state.

    Yields:
        A generator of template dictionaries with loaded definitions.
    """
    # Get the base directory for templates
    base_dir = Path(__file__).parent

    # Iterate over all JSON files in the templates directory
    template_dir = base_dir / "templates"
    for template_file in template_dir.glob("*.json"):
        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)

            # Filter any embedded definitions before attaching file-based overrides
            definition = template.get("definition")
            if isinstance(definition, str):
                template["definition"] = _strip_ruff_control_lines(definition)

            # Provide the file stem so the UI can suggest a default server name
            template["suggested_name"] = template_file.stem

            # If the template has a definition file, load its content
            if 'definition_file' in template:
                definition_path = base_dir / template['definition_file']
                try:
                    with open(definition_path, 'r', encoding='utf-8') as def_file:
                        template['definition'] = _strip_ruff_control_lines(def_file.read())
                except IOError as e:
                    print(f"Warning: Could not load definition file {definition_path}: {e}")
                    continue

            # Ensure we return a copy to prevent modification of the original
            yield dict(template)


def _strip_ruff_control_lines(definition: str) -> str:
    """Remove ruff control comments from the provided template definition."""

    lines = definition.splitlines()
    filtered_lines = [line for line in lines if not line.lstrip().startswith("# ruff")]

    if not filtered_lines:
        return ""

    stripped_definition = "\n".join(filtered_lines)

    if definition.endswith("\n"):
        stripped_definition += "\n"

    return stripped_definition
