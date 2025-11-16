"""Secret CRUD operations."""

from typing import List, Optional

from models import Secret
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Secret entities
_secret_repo = GenericEntityRepository(Secret)


def get_secrets() -> List[Secret]:
    """Return all secrets ordered by name."""
    return _secret_repo.get_all()


def get_template_secrets() -> List[Secret]:
    """Return template secrets from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_SECRETS, resolve_cid_value

    templates = get_templates_for_type(ENTITY_TYPE_SECRETS)

    # Convert template dicts to Secret objects (read-only representations)
    secret_objects = []
    for template in templates:
        # Create a minimal Secret object from template data
        secret = Secret()
        # Templates are not persisted DB rows, so id remains None
        secret.id = None
        # Store the template key in a separate attribute for UI use
        secret.template_key = template.get('key', '')
        secret.name = template.get('name', template.get('key', ''))

        # Try to get definition from various possible fields
        definition = template.get('definition')
        if not definition and template.get('definition_cid'):
            definition = resolve_cid_value(template.get('definition_cid'))
        if not definition and template.get('value_cid'):
            definition = resolve_cid_value(template.get('value_cid'))

        secret.definition = definition or ''
        secret.enabled = True
        secret.template = True  # Mark as template for backwards compatibility
        secret_objects.append(secret)

    return sorted(secret_objects, key=lambda s: s.name if s.name else '')


def get_secret_by_name(name: str) -> Optional[Secret]:
    """Return a secret by name."""
    return _secret_repo.get_by_name(name)


def get_first_secret_name() -> Optional[str]:
    """Return the first secret name ordered alphabetically."""
    return _secret_repo.get_first_name()


def count_secrets() -> int:
    """Return the count of secrets."""
    return _secret_repo.count()
