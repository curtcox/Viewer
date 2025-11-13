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
    """Return template variables from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_VARIABLES, resolve_cid_value

    templates = get_templates_for_type(user_id, ENTITY_TYPE_VARIABLES)

    # Convert template dicts to Variable objects (read-only representations)
    variable_objects = []
    for template in templates:
        # Create a minimal Variable object from template data
        variable = Variable()
        # Use template key as ID for UI to reference
        variable.id = template.get('key', '')
        variable.name = template.get('name', template.get('key', ''))
        variable.user_id = user_id

        # Try to get definition from various possible fields
        definition = template.get('definition')
        if not definition and template.get('definition_cid'):
            definition = resolve_cid_value(template.get('definition_cid'))

        variable.definition = definition or ''
        variable.enabled = True
        variable.template = True  # Mark as template for backwards compatibility
        variable_objects.append(variable)

    return sorted(variable_objects, key=lambda v: v.name if v.name else '')


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
