"""UI status helpers for displaying custom UI suggestions.

This module provides functions to generate UI suggestion links and
information for displaying in the view pages of aliases, servers, and variables.
"""

from typing import Any, Dict, List, Optional

from ui_manager import (
    get_uis_for_entity,
    get_ui_count_for_entity,
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
)


def _format_ui_count_label(count: int) -> str:
    """Format a count into a human-readable label.

    Args:
        count: Number of UIs

    Returns:
        Human-readable label like "No additional UIs", "1 additional UI",
        or "3 additional UIs"
    """
    if count == 0:
        return "No additional UIs"
    if count == 1:
        return "1 additional UI"
    return f"{count} additional UIs"


def get_ui_suggestions_info(
    entity_type: str,
    entity_name: str,
) -> Dict[str, Any]:
    """Get UI suggestions information for rendering in templates.

    Args:
        entity_type: Type of entity ('aliases', 'servers', 'variables')
        entity_name: Name of the specific entity

    Returns:
        Dictionary with:
        - 'has_uis': bool - whether any UIs are defined
        - 'count': int - number of UIs defined
        - 'uis': list - list of UI definitions with 'name' and 'path'
        - 'config_url': str - URL to configure UIs
        - 'label': str - human-readable label
    """
    uis = get_uis_for_entity(entity_type, entity_name)
    count = len(uis)
    has_uis = count > 0

    # URL to configure UIs
    config_url = '/variables/uis'

    return {
        'has_uis': has_uis,
        'count': count,
        'uis': uis,
        'config_url': config_url,
        'label': _format_ui_count_label(count),
    }


def generate_ui_suggestions_label(
    entity_type: str,
    entity_name: str,
) -> str:
    """Generate a human-readable label for UI suggestions.

    Args:
        entity_type: Type of entity ('aliases', 'servers', 'variables')
        entity_name: Name of the specific entity

    Returns:
        Human-readable status label:
        - "3 additional UIs" - When multiple UIs are defined
        - "1 additional UI" - When exactly one UI is defined
        - "No additional UIs" - When no UIs are defined
    """
    count = get_ui_count_for_entity(entity_type, entity_name)
    return _format_ui_count_label(count)
