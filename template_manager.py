"""Template management system for centralized template configuration.

This module provides functionality to manage templates stored in a centralized
JSON configuration in the 'templates' variable. Templates can be stored either
as direct JSON or as a CID reference to stored JSON.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from db_access.variables import get_variable_by_name
from db_access.cids import get_cid_by_path

logger = logging.getLogger(__name__)

# Template entity types
ENTITY_TYPE_ALIASES = 'aliases'
ENTITY_TYPE_SERVERS = 'servers'
ENTITY_TYPE_VARIABLES = 'variables'
ENTITY_TYPE_SECRETS = 'secrets'
ENTITY_TYPE_UPLOADS = 'uploads'

VALID_ENTITY_TYPES = {
    ENTITY_TYPE_ALIASES,
    ENTITY_TYPE_SERVERS,
    ENTITY_TYPE_VARIABLES,
    ENTITY_TYPE_SECRETS,
    ENTITY_TYPE_UPLOADS,
}


def get_templates_config() -> Optional[Dict[str, Any]]:
    """Read and parse the templates configuration.

    Returns:
        Parsed templates dictionary, or None if not found or invalid

    The templates variable can contain either:
    - Direct JSON: A JSON string with the templates structure
    - CID Reference: A CID string pointing to stored JSON
    """
    # Get the templates variable
    templates_var = get_variable_by_name('templates')
    if not templates_var or not templates_var.definition:
        return None

    definition = templates_var.definition.strip()
    if not definition:
        return None

    # Try to parse as direct JSON first
    try:
        templates_dict = json.loads(definition)
        if isinstance(templates_dict, dict):
            return templates_dict
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to resolve as CID reference
    # CID format: can be "/CID_VALUE" or just "CID_VALUE"
    cid_path = definition if definition.startswith('/') else f'/{definition}'

    try:
        cid_record = get_cid_by_path(cid_path)
        if cid_record and cid_record.file_data:
            json_data = cid_record.file_data.decode('utf-8')
            templates_dict = json.loads(json_data)
            if isinstance(templates_dict, dict):
                return templates_dict
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse CID templates: %s", e)
        return None

    logger.warning("Templates variable is not valid JSON or CID")
    return None


def validate_templates_json(json_data: str) -> Tuple[bool, Optional[str]]:
    """Validate templates JSON structure.

    Args:
        json_data: JSON string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if valid, False otherwise
        - error_message: Description of error if invalid, None if valid
    """
    if not json_data or not json_data.strip():
        return False, "Templates JSON cannot be empty"

    # Try to parse JSON
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"

    # Verify it's a dictionary
    if not isinstance(data, dict):
        return False, "Templates must be a JSON object (dictionary)"

    # Check for required top-level keys
    for entity_type in VALID_ENTITY_TYPES:
        if entity_type not in data:
            return False, f"Missing required key: '{entity_type}'"

        # Verify each entity type contains a dictionary
        if not isinstance(data[entity_type], dict):
            return False, f"'{entity_type}' must be an object (dictionary)"

        # Validate each template within the entity type
        for template_key, template_data in data[entity_type].items():
            if not isinstance(template_data, dict):
                return False, f"Template '{template_key}' in '{entity_type}' must be an object"

            # Check for required fields
            if 'name' not in template_data:
                return False, f"Template '{template_key}' in '{entity_type}' missing 'name' field"

    return True, None


def get_template_status() -> Dict[str, Any]:
    """Get template status information.

    Returns:
        Dictionary with status information:
        - is_valid: bool - whether templates are valid
        - error: str or None - error message if invalid
        - count_total: int - total number of templates
        - count_by_type: dict - count of templates by entity type
    """
    templates_config = get_templates_config()

    if templates_config is None:
        return {
            'is_valid': False,
            'error': None,
            'count_total': 0,
            'count_by_type': {
                ENTITY_TYPE_ALIASES: 0,
                ENTITY_TYPE_SERVERS: 0,
                ENTITY_TYPE_VARIABLES: 0,
                ENTITY_TYPE_SECRETS: 0,
                ENTITY_TYPE_UPLOADS: 0,
            },
        }

    # Count templates by type
    count_by_type = {}
    count_total = 0

    for entity_type in VALID_ENTITY_TYPES:
        type_templates = templates_config.get(entity_type, {})
        count = len(type_templates) if isinstance(type_templates, dict) else 0
        count_by_type[entity_type] = count
        count_total += count

    return {
        'is_valid': True,
        'error': None,
        'count_total': count_total,
        'count_by_type': count_by_type,
    }


def get_templates_for_type(entity_type: str) -> List[Dict[str, Any]]:
    """Extract templates for a specific entity type.

    Args:
        entity_type: Type of entity ('aliases', 'servers', 'variables', 'secrets')

    Returns:
        List of template definitions for the specified type.
        Each template is a dictionary with the template data plus a 'key' field.
    """
    if entity_type not in VALID_ENTITY_TYPES:
        logger.warning("Invalid entity type requested: %s", entity_type)
        return []

    templates_config = get_templates_config()
    if not templates_config:
        return []

    type_templates = templates_config.get(entity_type, {})
    if not isinstance(type_templates, dict):
        return []

    # Convert to list, adding the key to each template
    result = []
    for key, template_data in type_templates.items():
        if isinstance(template_data, dict):
            # Unpack template_data first, then override 'key' to ensure it matches the dict key
            template_with_key = {**template_data, 'key': key}
            result.append(template_with_key)

    return result


def get_template_by_key(
    user_id: str, entity_type: str, template_key: str
) -> Optional[Dict[str, Any]]:
    """Get a specific template by its key.

    Args:
        user_id: User identifier
        entity_type: Type of entity ('aliases', 'servers', 'variables', 'secrets')
        template_key: The key/identifier of the template

    Returns:
        Template dictionary if found, None otherwise
    """
    if entity_type not in VALID_ENTITY_TYPES:
        logger.warning("Invalid entity type requested: %s", entity_type)
        return None

    templates_config = get_templates_config(user_id)
    if not templates_config:
        return None

    type_templates = templates_config.get(entity_type, {})
    if not isinstance(type_templates, dict):
        return None

    template_data = type_templates.get(template_key)
    if template_data and isinstance(template_data, dict):
        # Clone template_data and set 'key' only if not present
        result = dict(template_data)
        result.setdefault('key', template_key)
        return result

    return None


def resolve_cid_value(cid_or_value: str) -> Optional[str]:
    """Resolve a CID reference to its actual value.

    Args:
        cid_or_value: Either a CID reference or a direct value

    Returns:
        The resolved value if the CID is found and can be decoded,
        or the original input string if CID resolution fails
    """
    if not cid_or_value:
        return None

    # Check if it looks like a CID (base64-like pattern)
    # For now, assume any non-empty string starting with uppercase or containing base64 chars
    # is potentially a CID
    if cid_or_value.startswith('/'):
        cid_path = cid_or_value
    else:
        # Try as CID
        cid_path = f'/{cid_or_value}'

    try:
        cid_record = get_cid_by_path(cid_path)
        if cid_record and cid_record.file_data:
            return cid_record.file_data.decode('utf-8')
    except (UnicodeDecodeError, KeyError, AttributeError, TypeError) as e:
        # UnicodeDecodeError: file_data cannot be decoded as UTF-8
        # KeyError: CID lookup failed
        # AttributeError: cid_record or file_data is None
        # TypeError: unexpected type in processing
        logger.debug("Could not resolve CID %s: %s", cid_or_value, e)

    # Return the original value if not a CID or couldn't resolve
    return cid_or_value
