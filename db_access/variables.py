"""Variable CRUD operations."""

from typing import List, Optional

from models import Variable


def get_user_variables(user_id: str) -> List[Variable]:
    """Return all variables for a user ordered by name."""
    return Variable.query.filter_by(user_id=user_id).order_by(Variable.name).all()


def get_user_template_variables(user_id: str) -> List[Variable]:
    """Return template variables for a user ordered by name."""
    return (
        Variable.query.filter_by(user_id=user_id, template=True)
        .order_by(Variable.name)
        .all()
    )


def get_variable_by_name(user_id: str, name: str) -> Optional[Variable]:
    """Return a variable by name for a user."""
    return Variable.query.filter_by(user_id=user_id, name=name).first()


def get_first_variable_name(user_id: str) -> Optional[str]:
    """Return the first variable name for a user ordered alphabetically."""
    variable = (
        Variable.query.filter_by(user_id=user_id)
        .order_by(Variable.name.asc())
        .first()
    )
    return variable.name if variable else None


def count_user_variables(user_id: str) -> int:
    """Return the count of variables for a user."""
    return Variable.query.filter_by(user_id=user_id).count()


def count_variables() -> int:
    """Return the total count of variables."""
    return Variable.query.count()

