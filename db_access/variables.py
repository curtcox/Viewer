"""Variable CRUD operations."""

from typing import List, Optional

from models import Variable
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Variable entities
_variable_repo = GenericEntityRepository(Variable)


def get_user_variables(user_id: str) -> List[Variable]:
    """Return all variables for a user ordered by name."""
    return _variable_repo.get_all_for_user(user_id)


def get_user_template_variables(user_id: str) -> List[Variable]:
    """Return template variables for a user ordered by name."""
    return _variable_repo.get_templates_for_user(user_id)


def get_variable_by_name(user_id: str, name: str) -> Optional[Variable]:
    """Return a variable by name for a user."""
    return _variable_repo.get_by_name(user_id, name)


def get_first_variable_name(user_id: str) -> Optional[str]:
    """Return the first variable name for a user ordered alphabetically."""
    return _variable_repo.get_first_name(user_id)


def count_user_variables(user_id: str) -> int:
    """Return the count of variables for a user."""
    return _variable_repo.count_for_user(user_id)


def count_variables() -> int:
    """Return the total count of variables."""
    return _variable_repo.count_all()
