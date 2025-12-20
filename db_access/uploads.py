"""Upload template operations."""

from typing import Any, Dict, List


def get_template_uploads() -> List[Dict[str, Any]]:
    """Return template uploads from templates variable configuration.

    Returns:
        List of dictionaries with upload template data.
        Each dict contains: id, name, content
    """
    from template_manager import (
        get_templates_for_type,
        ENTITY_TYPE_UPLOADS,
        resolve_cid_value,
    )

    templates = get_templates_for_type(ENTITY_TYPE_UPLOADS)

    # Convert template dicts to upload template format for the UI
    upload_templates = []
    for template in templates:
        template_key = template.get("key", "")
        template_name = template.get("name", template_key)

        # Try to get content from various possible fields
        content = template.get("content")
        if not content and template.get("content_cid"):
            content = resolve_cid_value(template.get("content_cid"))

        upload_templates.append(
            {
                "id": template_key,
                "name": template_name,
                "content": content or "",
                "description": template.get("description", ""),
            }
        )

    return sorted(upload_templates, key=lambda t: t["name"])
