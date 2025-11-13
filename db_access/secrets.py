"""Secret CRUD operations."""

from typing import List, Optional

from models import Secret
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Secret entities
_secret_repo = GenericEntityRepository(Secret)


def get_user_secrets(user_id: str) -> List[Secret]:
    """Return all secrets for a user ordered by name."""
    return _secret_repo.get_all_for_user(user_id)


def get_user_template_secrets(user_id: str) -> List[Secret]:
    """Return template secrets from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_SECRETS, resolve_cid_value

    templates = get_templates_for_type(user_id, ENTITY_TYPE_SECRETS)

    # Convert template dicts to Secret objects (read-only representations)
    secret_objects = []
    for template in templates:
        # Create a minimal Secret object from template data
        secret = Secret()
        # Use template key as ID for UI to reference
        secret.id = template.get('key', '')
        secret.name = template.get('name', template.get('key', ''))
        secret.user_id = user_id

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


def get_secret_by_name(user_id: str, name: str) -> Optional[Secret]:
    """Return a secret by name for a user."""
    return _secret_repo.get_by_name(user_id, name)


def get_first_secret_name(user_id: str) -> Optional[str]:
    """Return the first secret name for a user ordered alphabetically."""
    return _secret_repo.get_first_name(user_id)


def count_user_secrets(user_id: str) -> int:
    """Return the count of secrets for a user."""
    return _secret_repo.count_for_user(user_id)


def count_secrets() -> int:
    """Return the total count of secrets."""
    return _secret_repo.count_all()
