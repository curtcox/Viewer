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
    """Return template secrets for a user ordered by name."""
    return _secret_repo.get_templates_for_user(user_id)


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
