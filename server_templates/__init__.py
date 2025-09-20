"""Server templates package for the Viewer application.

This package contains predefined server templates that can be used to create new servers.
"""

from __future__ import annotations

from typing import Iterable, Dict, Any
import json
from pathlib import Path

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
            
            # If the template has a definition file, load its content
            if 'definition_file' in template:
                definition_path = base_dir / template['definition_file']
                try:
                    with open(definition_path, 'r', encoding='utf-8') as def_file:
                        template['definition'] = def_file.read()
                except IOError as e:
                    print(f"Warning: Could not load definition file {definition_path}: {e}")
                    continue
            
            # Ensure we return a copy to prevent modification of the original
            yield dict(template)
