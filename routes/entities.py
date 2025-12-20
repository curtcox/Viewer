"""Shared CRUD helper utilities for route modules."""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type

from logfire_utils import instrument as logfire_instrument
from flask import flash
from markupsafe import Markup, escape

from cid_utils import save_server_definition_as_cid
from db_access import (
    EntityInteractionRequest,
    get_secret_by_name,
    get_server_by_name,
    get_variable_by_name,
    record_entity_interaction,
    save_entity,
)


# Type-based dispatch for entity operations
# This eliminates fragile string-based type checking


class EntityTypeRegistry:
    """Registry for entity type-specific operations.

    This class provides type-safe dispatch for operations that differ
    based on entity type, eliminating the need for string-based type checking.
    """

    def __init__(self):
        """Initialize the registry with entity type mappings."""
        # Import models lazily to avoid circular dependencies
        from models import Secret, Server, Variable

        # Map entity classes to their get_by_name functions
        self._get_by_name_funcs: Dict[Type, Callable] = {
            Server: get_server_by_name,
            Variable: get_variable_by_name,
            Secret: get_secret_by_name,
        }

        # Map entity classes to their CID update functions
        self._cid_update_funcs: Dict[Type, Callable] = {}

    def get_by_name(self, entity_class: Type, name: str) -> Optional[Any]:
        """Get entity by name using type dispatch.

        Args:
            entity_class: Entity model class
            name: Entity name

        Returns:
            Entity instance or None if not found

        Raises:
            ValueError: If entity_class is not registered in the registry
        """
        func = self._get_by_name_funcs.get(entity_class)
        if func is None:
            raise ValueError(
                f"Unregistered entity type: {entity_class.__name__}. "
                f"Entity type must be registered in EntityTypeRegistry._get_by_name_funcs. "
                f"Registered types: {', '.join(cls.__name__ for cls in self._get_by_name_funcs)}"
            )
        return func(name)

    def update_definitions_cid(self, entity_class: Type) -> Optional[str]:
        """Update definitions CID for entity type.

        Args:
            entity_class: Entity model class

        Returns:
            Updated CID or None if not applicable
        """
        # Lazy load CID update functions to avoid circular imports
        if not self._cid_update_funcs:
            from .secrets import update_secret_definitions_cid
            from .servers import update_server_definitions_cid
            from .variables import update_variable_definitions_cid
            from models import Secret, Server, Variable

            self._cid_update_funcs = {
                Server: update_server_definitions_cid,
                Variable: update_variable_definitions_cid,
                Secret: update_secret_definitions_cid,
            }

        func = self._cid_update_funcs.get(entity_class)
        if func is None:
            return None
        return func()

    def requires_definition_cid(self, entity_class: Type) -> bool:
        """Check if entity type requires definition CID storage.

        Args:
            entity_class: Entity model class

        Returns:
            True if entity needs definition CID
        """
        from models import Server

        return entity_class is Server


# Global registry instance
_entity_registry = EntityTypeRegistry()


def check_name_exists(
    model_class: Type[Any], name: str, exclude_id: Any = None
) -> bool:
    """Check if a name already exists for a user, optionally excluding a specific record."""
    entity = _entity_registry.get_by_name(model_class, name)

    if entity and exclude_id and getattr(entity, "id", None) == exclude_id:
        return False
    return entity is not None


@logfire_instrument(
    "entities.create_entity({model_class=}, {form=}, {entity_type=})",
    extract_args=True,
    record_return=True,
)
def create_entity(
    model_class: Type[Any],
    form,
    entity_type: str,
    *,
    change_message: str | None = None,
    content_text: str | None = None,
) -> bool:
    """Generic function to create a new entity (server, variable, or secret)."""
    if check_name_exists(model_class, form.name.data):
        flash(
            Markup('A {entity} named "{name}" already exists').format(
                entity=escape(entity_type),
                name=escape(form.name.data),
            ),
            "danger",
        )
        return False

    entity_data = {
        "name": form.name.data,
        "definition": form.definition.data,
    }

    enabled_field = getattr(form, "enabled", None)
    if enabled_field is not None:
        entity_data["enabled"] = bool(enabled_field.data)

    if _entity_registry.requires_definition_cid(model_class):
        definition_cid = save_server_definition_as_cid(form.definition.data)
        entity_data["definition_cid"] = definition_cid

    entity = model_class(**entity_data)
    save_entity(entity)

    if content_text is None:
        content_text = getattr(form, "definition", None)
        if content_text is not None:
            content_text = content_text.data or ""
        else:
            content_text = ""

    record_entity_interaction(
        EntityInteractionRequest(
            entity_type=entity_type,
            entity_name=form.name.data,
            action="save",
            message=change_message or "",
            content=content_text,
        )
    )

    _entity_registry.update_definitions_cid(model_class)

    flash(
        Markup('{entity} "{name}" created successfully!').format(
            entity=escape(entity_type.title()),
            name=escape(form.name.data),
        ),
        "success",
    )
    return True


@logfire_instrument(
    "entities.update_entity({entity=}, {form=}, {entity_type=})",
    extract_args=True,
    record_return=True,
)
def update_entity(
    entity,
    form,
    entity_type: str,
    change_message: str | None = None,
    content_text: str | None = None,
) -> bool:
    """Generic function to update an entity (server, variable, or secret)."""
    if form.name.data != entity.name:
        if check_name_exists(type(entity), form.name.data, entity.id):
            flash(
                Markup('A {entity} named "{name}" already exists').format(
                    entity=escape(entity_type),
                    name=escape(form.name.data),
                ),
                "danger",
            )
            return False

    if _entity_registry.requires_definition_cid(type(entity)):
        if form.definition.data != entity.definition:
            definition_cid = save_server_definition_as_cid(form.definition.data)
            entity.definition_cid = definition_cid

    entity.name = form.name.data
    entity.definition = form.definition.data
    entity.updated_at = datetime.now(timezone.utc)

    enabled_field = getattr(form, "enabled", None)
    if enabled_field is not None:
        entity.enabled = bool(enabled_field.data)

    save_entity(entity)

    if content_text is None:
        content_text = getattr(form, "definition", None)
        if content_text is not None:
            content_text = content_text.data or ""
        else:
            content_text = ""

    record_entity_interaction(
        EntityInteractionRequest(
            entity_type=entity_type,
            entity_name=entity.name,
            action="save",
            message=change_message or "",
            content=content_text,
        )
    )

    _entity_registry.update_definitions_cid(type(entity))

    flash(
        Markup('{entity} "{name}" updated successfully!').format(
            entity=escape(entity_type.title()),
            name=escape(entity.name),
        ),
        "success",
    )
    return True


__all__ = ["check_name_exists", "create_entity", "update_entity"]
