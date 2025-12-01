"""UI manager for custom UI suggestions.

This module provides functionality to manage custom UIs stored in a centralized
JSON configuration in the 'uis' variable. UIs can be stored either
as direct JSON or as a CID reference to stored JSON.

The 'uis' variable should contain JSON with the following structure:
{
    "aliases": {
        "my-alias": [
            {"name": "Dashboard View", "path": "/path/to/dashboard"},
            {"name": "Graph View", "path": "/path/to/graph"}
        ]
    },
    "servers": {
        "my-server": [
            {"name": "Debug UI", "path": "/debug/my-server"}
        ]
    },
    "variables": {
        "my-variable": [
            {"name": "Editor", "path": "/edit/my-variable"}
        ]
    }
}
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from db_access.variables import get_variable_by_name
from db_access.cids import get_cid_by_path

logger = logging.getLogger(__name__)

# UI entity types
ENTITY_TYPE_ALIASES = 'aliases'
ENTITY_TYPE_SERVERS = 'servers'
ENTITY_TYPE_VARIABLES = 'variables'

VALID_ENTITY_TYPES = {
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
}


def get_uis_config() -> Optional[Dict[str, Any]]:
    """Read and parse the UIs configuration.

    Returns:
        Parsed UIs dictionary, or None if not found or invalid

    The uis variable can contain either:
    - Direct JSON: A JSON string with the UIs structure
    - CID Reference: A CID string pointing to stored JSON
    """
    # Get the uis variable
    uis_var = get_variable_by_name('uis')
    if not uis_var or not uis_var.definition:
        return None

    definition = uis_var.definition.strip()
    if not definition:
        return None

    # Try to parse as direct JSON first
    try:
        uis_dict = json.loads(definition)
        if isinstance(uis_dict, dict):
            return uis_dict
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to resolve as CID reference
    # CID format: can be "/CID_VALUE" or just "CID_VALUE"
    cid_path = definition if definition.startswith('/') else f'/{definition}'

    try:
        cid_record = get_cid_by_path(cid_path)
        if cid_record and cid_record.file_data:
            json_data = cid_record.file_data.decode('utf-8')
            uis_dict = json.loads(json_data)
            if isinstance(uis_dict, dict):
                return uis_dict
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse CID UIs: %s", e)
        return None

    logger.warning("UIs variable is not valid JSON or CID")
    return None


def validate_uis_json(json_data: str) -> Tuple[bool, Optional[str]]:
    """Validate UIs JSON structure.

    Args:
        json_data: JSON string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if valid, False otherwise
        - error_message: Description of error if invalid, None if valid
    """
    if not json_data or not json_data.strip():
        return False, "UIs JSON cannot be empty"

    # Try to parse JSON
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"

    # Verify it's a dictionary
    if not isinstance(data, dict):
        return False, "UIs must be a JSON object (dictionary)"

    # Validate structure for each entity type present
    for entity_type in VALID_ENTITY_TYPES:
        if entity_type not in data:
            continue  # Entity types are optional

        if not isinstance(data[entity_type], dict):
            return False, f"'{entity_type}' must be an object (dictionary)"

        # Validate each entity's UIs
        for entity_name, uis in data[entity_type].items():
            if not isinstance(uis, list):
                return False, f"UIs for '{entity_name}' in '{entity_type}' must be an array"

            for i, ui in enumerate(uis):
                if not isinstance(ui, dict):
                    return False, (
                        f"UI at index {i} for '{entity_name}' in '{entity_type}' must be an object"
                    )
                if 'name' not in ui:
                    return False, (
                        f"UI at index {i} for '{entity_name}' in '{entity_type}' "
                        f"missing 'name' field"
                    )
                if 'path' not in ui:
                    return False, (
                        f"UI at index {i} for '{entity_name}' in '{entity_type}' "
                        f"missing 'path' field"
                    )

    return True, None


def get_uis_for_entity(entity_type: str, entity_name: str) -> List[Dict[str, str]]:
    """Get custom UIs for a specific entity.

    Args:
        entity_type: Type of entity ('aliases', 'servers', 'variables')
        entity_name: Name of the specific entity

    Returns:
        List of UI definitions for the specified entity.
        Each UI is a dictionary with 'name' and 'path' fields.
    """
    if entity_type not in VALID_ENTITY_TYPES:
        logger.warning("Invalid entity type requested: %s", entity_type)
        return []

    uis_config = get_uis_config()
    if not uis_config:
        return []

    type_uis = uis_config.get(entity_type, {})
    if not isinstance(type_uis, dict):
        return []

    entity_uis = type_uis.get(entity_name, [])
    if not isinstance(entity_uis, list):
        return []

    # Filter to only include valid UI entries
    result = []
    for ui in entity_uis:
        if isinstance(ui, dict) and 'name' in ui and 'path' in ui:
            result.append({
                'name': str(ui['name']),
                'path': str(ui['path']),
            })

    return result


def get_ui_count_for_entity(entity_type: str, entity_name: str) -> int:
    """Get the count of custom UIs for a specific entity.

    Args:
        entity_type: Type of entity ('aliases', 'servers', 'variables')
        entity_name: Name of the specific entity

    Returns:
        Number of UIs defined for the entity
    """
    return len(get_uis_for_entity(entity_type, entity_name))


def get_uis_status() -> Dict[str, Any]:
    """Get UIs status information.

    Returns:
        Dictionary with status information:
        - is_valid: bool - whether UIs are valid
        - error: str or None - error message if invalid
        - count_total: int - total number of entity-UI mappings
        - count_by_type: dict - count of entity-UI mappings by entity type
    """
    uis_config = get_uis_config()

    if uis_config is None:
        return {
            'is_valid': False,
            'error': None,
            'count_total': 0,
            'count_by_type': {
                ENTITY_TYPE_ALIASES: 0,
                ENTITY_TYPE_SERVERS: 0,
                ENTITY_TYPE_VARIABLES: 0,
            },
        }

    # Count entities with UIs by type
    count_by_type = {}
    count_total = 0

    for entity_type in VALID_ENTITY_TYPES:
        type_uis = uis_config.get(entity_type, {})
        count = len(type_uis) if isinstance(type_uis, dict) else 0
        count_by_type[entity_type] = count
        count_total += count

    return {
        'is_valid': True,
        'error': None,
        'count_total': count_total,
        'count_by_type': count_by_type,
    }
