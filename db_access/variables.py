"""Variable CRUD operations."""

from typing import List, Optional

from models import Variable
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Variable entities
_variable_repo = GenericEntityRepository(Variable)


def get_variables() -> List[Variable]:
    """Return all variables ordered by name."""
    return _variable_repo.get_all()


def get_template_variables() -> List[Variable]:
    """Return template variables from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_VARIABLES, resolve_cid_value

    templates = get_templates_for_type(ENTITY_TYPE_VARIABLES)

    # Convert template dicts to Variable objects (read-only representations)
    variable_objects = []
    for template in templates:
        # Create a minimal Variable object from template data
        variable = Variable()
        # Templates are not persisted DB rows, so id remains None
        variable.id = None
        # Store the template key in a separate attribute for UI use
        variable.template_key = template.get('key', '')
        variable.name = template.get('name', template.get('key', ''))

        # Try to get definition from various possible fields
        definition = template.get('definition')
        if not definition and template.get('definition_cid'):
            definition = resolve_cid_value(template.get('definition_cid'))

        variable.definition = definition or ''
        variable.enabled = True
        variable.template = True  # Mark as template for backwards compatibility
        variable_objects.append(variable)

    return sorted(variable_objects, key=lambda v: v.name if v.name else '')


def get_variable_by_name(name: str) -> Optional[Variable]:
    """Return a variable by name."""
    return _variable_repo.get_by_name(name)


def get_first_variable_name() -> Optional[str]:
    """Return the first variable name ordered alphabetically."""
    return _variable_repo.get_first_name()


def count_variables() -> int:
    """Return the count of variables."""
    return _variable_repo.count()
