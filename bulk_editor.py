"""Generic bulk JSON editor for entity collections.

This module provides a reusable abstraction for bulk editing entity collections
through JSON payloads, eliminating duplication across variables, secrets, etc.
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Generic, List, Optional, Pattern, Protocol, Tuple, Type, TypeVar

from constants import Patterns

if TYPE_CHECKING:
    from db_access import delete_entity, save_entity
    from models import Secret, Variable


class EntityProtocol(Protocol):
    """Protocol defining the required interface for bulk-editable entities."""
    name: str
    definition: str
    user_id: str
    updated_at: datetime


# TypeVar for generic entity type bound to EntityProtocol
T = TypeVar('T', bound=EntityProtocol)

# Validation result: (parsed_dict_or_none, error_message_or_none)
ValidationResult = Tuple[Optional[Dict[str, str]], Optional[str]]


class BulkEditorHandler(Generic[T]):
    """Handle bulk JSON editing for entity collections.

    This class provides a generic pattern for:
    - Building JSON payloads from entity collections
    - Parsing and validating JSON payloads
    - Applying bulk changes (add, update, delete)

    Args:
        entity_class: SQLAlchemy model class (Variable, Secret, etc.)
        entity_type_name: Human-readable name for error messages ("variable", "secret")
        name_pattern: Regex pattern for validating entity names
    """

    def __init__(
        self,
        entity_class: Type[T],
        entity_type_name: str,
        name_pattern: Pattern[str],
    ):
        """Initialize bulk editor handler.

        Args:
            entity_class: SQLAlchemy model class
            entity_type_name: Human-readable entity type name (lowercase)
            name_pattern: Compiled regex for name validation
        """
        self.entity_class = entity_class
        self.entity_type_name = entity_type_name
        self.name_pattern = name_pattern

    def build_payload(self, entities: List[T]) -> str:
        """Convert entity list to JSON payload for bulk editing.

        Args:
            entities: List of entity objects with 'name' and 'definition' attributes

        Returns:
            Formatted JSON string with name->definition mapping
        """
        return json.dumps(
            {entity.name: entity.definition for entity in entities},
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        )

    def parse_payload(self, raw_payload: str) -> ValidationResult:
        """Validate and parse JSON payload from bulk editor.

        Args:
            raw_payload: Raw JSON string from user input

        Returns:
            Tuple of (parsed_dict, error_message)
            - On success: (dict, None)
            - On failure: (None, error_message)
        """
        # Parse JSON
        try:
            loaded = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            return None, f"Invalid JSON: {exc.msg}"

        # Validate top-level structure
        if not isinstance(loaded, dict):
            return None, (
                f"{self.entity_type_name.capitalize()} JSON must be an object "
                f"mapping {self.entity_type_name} names to values."
            )

        # Validate and normalize each entry
        normalized: Dict[str, str] = {}
        for name, value in loaded.items():
            # Validate name type
            if not isinstance(name, str):
                return None, f"All {self.entity_type_name} names must be strings."

            # Validate name pattern
            if not self.name_pattern.fullmatch(name):
                return None, (
                    f'Invalid {self.entity_type_name} name "{name}". '
                    f"{self.entity_type_name.capitalize()} names may only contain "
                    "letters, numbers, dots, hyphens, and underscores."
                )

            # Normalize value to string
            if isinstance(value, str):
                normalized[name] = value
            else:
                # Non-string values are JSON-encoded
                normalized[name] = json.dumps(value, ensure_ascii=False)

        return normalized, None

    def apply_changes(
        self,
        user_id: str,
        desired_values: Dict[str, str],
        existing: List[T],
    ) -> None:
        """Apply bulk changes to entity collection.

        This method handles:
        - Deleting entities that are no longer in desired set
        - Creating new entities that don't exist
        - Updating existing entities with changed definitions

        Args:
            user_id: User identifier
            desired_values: Dict of name->definition for desired final state
            existing: Current list of entities
        """
        from db_access import delete_entity, save_entity

        # Build lookup for existing entities
        existing_by_name = {entity.name: entity for entity in existing}
        desired_names = set(desired_values.keys())

        # Delete entities no longer in desired set
        # Sorted for deterministic ordering
        for name in sorted(set(existing_by_name.keys()) - desired_names):
            delete_entity(existing_by_name[name])

        # Create or update entities
        for name, definition in desired_values.items():
            current = existing_by_name.get(name)

            if current is None:
                # Create new entity
                new_entity = self.entity_class(  # type: ignore[call-arg]
                    name=name,
                    definition=definition,
                    user_id=user_id,
                )
                save_entity(new_entity)
            elif current.definition != definition:
                # Update existing entity if definition changed
                current.definition = definition
                current.updated_at = datetime.now(timezone.utc)
                save_entity(current)


# Pre-configured handlers for common entity types
# These can be imported and used directly


def create_variable_bulk_handler() -> "BulkEditorHandler[Variable]":
    """Create a bulk editor handler for variables.

    Returns:
        Configured BulkEditorHandler for Variable entities
    """
    from models import Variable
    return BulkEditorHandler(Variable, "variable", Patterns.ENTITY_NAME)


def create_secret_bulk_handler() -> "BulkEditorHandler[Secret]":
    """Create a bulk editor handler for secrets.

    Returns:
        Configured BulkEditorHandler for Secret entities
    """
    from models import Secret
    return BulkEditorHandler(Secret, "secret", Patterns.ENTITY_NAME)
