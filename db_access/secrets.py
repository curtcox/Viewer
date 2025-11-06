"""Secret CRUD operations."""

from typing import List, Optional

from models import Secret


def get_user_secrets(user_id: str) -> List[Secret]:
    """Return all secrets for a user ordered by name."""
    return Secret.query.filter_by(user_id=user_id).order_by(Secret.name).all()


def get_user_template_secrets(user_id: str) -> List[Secret]:
    """Return template secrets for a user ordered by name."""
    return (
        Secret.query.filter_by(user_id=user_id, template=True)
        .order_by(Secret.name)
        .all()
    )


def get_secret_by_name(user_id: str, name: str) -> Optional[Secret]:
    """Return a secret by name for a user."""
    return Secret.query.filter_by(user_id=user_id, name=name).first()


def get_first_secret_name(user_id: str) -> Optional[str]:
    """Return the first secret name for a user ordered alphabetically."""
    secret = (
        Secret.query.filter_by(user_id=user_id)
        .order_by(Secret.name.asc())
        .first()
    )
    return secret.name if secret else None


def count_user_secrets(user_id: str) -> int:
    """Return the count of secrets for a user."""
    return Secret.query.filter_by(user_id=user_id).count()


def count_secrets() -> int:
    """Return the total count of secrets."""
    return Secret.query.count()
