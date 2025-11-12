"""Utilities for building template data structures.

This module consolidates common patterns for building template lists
and other data structures used in route templates.
"""

from typing import Any, Iterable, List, Dict, Optional


def build_template_list(
    entities: Iterable[Any],
    prefix: Optional[str] = 'user',
    include_suggested_name: bool = True
) -> List[Dict[str, Any]]:
    """Build a template list for entity create/edit forms.

    This pattern appears in servers, variables, secrets, and aliases routes
    when building lists of template entities for users to copy from.

    Args:
        entities: Iterable of entity objects (Server, Variable, Secret, Alias)
        prefix: Optional prefix for the template ID (default: 'user')
        include_suggested_name: Whether to generate suggested names (default: True)

    Returns:
        List of dictionaries with template data

    Example:
        >>> servers = get_user_template_servers(user_id)
        >>> templates = build_template_list(servers)
        >>> # Returns:
        >>> # [
        >>> #     {
        >>> #         'id': 'user-1',
        >>> #         'name': 'api',
        >>> #         'definition': 'def main(): ...',
        >>> #         'suggested_name': 'api-copy'
        >>> #     },
        >>> #     ...
        >>> # ]
    """
    templates = []

    for entity in entities:
        entity_id = getattr(entity, 'id', None)
        entity_name = getattr(entity, 'name', '')
        entity_definition = getattr(entity, 'definition', '') or ''

        template_data = {
            'id': f'{prefix}-{entity_id}' if prefix and entity_id else entity_id,
            'name': entity_name,
            'definition': entity_definition,
        }

        if include_suggested_name:
            suggested = f"{entity_name}-copy" if entity_name else ''
            template_data['suggested_name'] = suggested

        templates.append(template_data)

    return templates


def build_entity_metadata_context(
    entity: Any,
    entity_type: str,
    definitions_cid: Optional[str] = None
) -> Dict[str, Any]:
    """Build common context data for entity views.

    Args:
        entity: Entity object to build context for
        entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
        definitions_cid: Optional CID for entity definitions

    Returns:
        Dictionary with common context data

    Example:
        >>> context = build_entity_metadata_context(server, 'server', cid_value)
        >>> # Returns:
        >>> # {
        >>> #     'entity_type': 'server',
        >>> #     'entity_name': 'api',
        >>> #     'definitions_cid': 'QmABC...'
        >>> # }
    """
    context = {
        'entity_type': entity_type,
        'entity_name': getattr(entity, 'name', None),
    }

    if definitions_cid:
        context['definitions_cid'] = definitions_cid

    return context
