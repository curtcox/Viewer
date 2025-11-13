"""Template status helpers for UI display.

This module provides functions to generate human-readable status labels and
link information for displaying template status in the UI.
"""

from typing import Dict, Optional

from template_manager import get_template_status


def generate_template_status_label(
    user_id: str, entity_type: Optional[str] = None
) -> str:
    """Generate a human-readable status label for templates.

    Args:
        user_id: User identifier
        entity_type: Optional entity type to show count for specific type only
                    (e.g., 'aliases', 'servers', 'variables', 'secrets')
                    If None, shows total count across all types

    Returns:
        Human-readable status label:
        - "11 templates" - When templates exist and are valid
        - "1 template" - When exactly one template exists
        - "No templates" - When templates variable is empty or doesn't exist
        - "Invalid template definition" - When JSON is malformed or CID is invalid
    """
    if not user_id:
        return "No templates"

    status = get_template_status(user_id)

    # Check if templates are invalid
    if not status['is_valid'] and status['count_total'] == 0:
        # No templates defined
        return "No templates"

    if status.get('error'):
        return "Invalid template definition"

    # Get count
    if entity_type:
        count = status['count_by_type'].get(entity_type, 0)
    else:
        count = status['count_total']

    # Format label
    if count == 0:
        return "No templates"
    elif count == 1:
        return "1 template"
    else:
        return f"{count} templates"


def get_template_link_info(
    user_id: str, entity_type: Optional[str] = None
) -> Dict[str, str]:
    """Get template status link information for rendering in templates.

    Args:
        user_id: User identifier
        entity_type: Optional entity type filter

    Returns:
        Dictionary with:
        - 'label': Human-readable status label
        - 'url': URL to templates configuration page
        - 'css_class': CSS class for styling based on status
    """
    if not user_id:
        return {
            'label': 'No templates',
            'url': '/variables/templates',
            'css_class': 'template-status-empty',
        }

    status = get_template_status(user_id)
    label = generate_template_status_label(user_id, entity_type)

    # Determine URL
    url = '/variables/templates'
    if entity_type:
        url = f'/variables/templates?type={entity_type}'

    # Determine CSS class
    css_class = 'template-status-empty'
    if status.get('error'):
        css_class = 'template-status-error'
    elif status['is_valid'] and status['count_total'] > 0:
        css_class = 'template-status-active'

    return {
        'label': label,
        'url': url,
        'css_class': css_class,
    }
