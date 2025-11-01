"""Shared CRUD helper utilities for route modules."""
from datetime import datetime, timezone
from typing import Any, Type

import logfire
from flask import flash

from cid_utils import save_server_definition_as_cid
from db_access import (
    EntityInteractionRequest,
    get_secret_by_name,
    get_server_by_name,
    get_variable_by_name,
    record_entity_interaction,
    save_entity,
)


def check_name_exists(model_class: Type[Any], name: str, user_id: str, exclude_id: Any = None) -> bool:
    """Check if a name already exists for a user, optionally excluding a specific record."""
    if model_class.__name__ == 'Server':
        entity = get_server_by_name(user_id, name)
    elif model_class.__name__ == 'Variable':
        entity = get_variable_by_name(user_id, name)
    elif model_class.__name__ == 'Secret':
        entity = get_secret_by_name(user_id, name)
    else:
        entity = None

    if entity and exclude_id and getattr(entity, 'id', None) == exclude_id:
        return False
    return entity is not None


@logfire.instrument("entities.create_entity({model_class=}, {form=}, {user_id=}, {entity_type=})", extract_args=True, record_return=True)
def create_entity(
    model_class: Type[Any],
    form,
    user_id: str,
    entity_type: str,
    *,
    change_message: str | None = None,
    content_text: str | None = None,
) -> bool:
    """Generic function to create a new entity (server, variable, or secret)."""
    if check_name_exists(model_class, form.name.data, user_id):
        flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
        return False

    entity_data = {
        'name': form.name.data,
        'definition': form.definition.data,
        'user_id': user_id,
    }

    enabled_field = getattr(form, 'enabled', None)
    if enabled_field is not None:
        entity_data['enabled'] = bool(enabled_field.data)

    template_field = getattr(form, 'template', None)
    if template_field is not None:
        entity_data['template'] = bool(template_field.data)

    if model_class.__name__ == 'Server':
        definition_cid = save_server_definition_as_cid(form.definition.data, user_id)
        entity_data['definition_cid'] = definition_cid

    entity = model_class(**entity_data)
    save_entity(entity)

    if content_text is None:
        content_text = getattr(form, 'definition', None)
        if content_text is not None:
            content_text = content_text.data or ''
        else:
            content_text = ''

    record_entity_interaction(
        EntityInteractionRequest(
            user_id=user_id,
            entity_type=entity_type,
            entity_name=form.name.data,
            action='save',
            message=change_message or '',
            content=content_text,
        )
    )

    if model_class.__name__ == 'Server':
        from .servers import update_server_definitions_cid

        update_server_definitions_cid(user_id)
    elif model_class.__name__ == 'Variable':
        from .variables import update_variable_definitions_cid

        update_variable_definitions_cid(user_id)
    elif model_class.__name__ == 'Secret':
        from .secrets import update_secret_definitions_cid

        update_secret_definitions_cid(user_id)

    flash(f'{entity_type.title()} "{form.name.data}" created successfully!', 'success')
    return True


@logfire.instrument("entities.update_entity({entity=}, {form=}, {entity_type=})", extract_args=True, record_return=True)
def update_entity(
    entity,
    form,
    entity_type: str,
    change_message: str | None = None,
    content_text: str | None = None,
) -> bool:
    """Generic function to update an entity (server, variable, or secret)."""
    if form.name.data != entity.name:
        if check_name_exists(type(entity), form.name.data, entity.user_id, entity.id):
            flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
            return False

    if type(entity).__name__ == 'Server':
        if form.definition.data != entity.definition:
            definition_cid = save_server_definition_as_cid(form.definition.data, entity.user_id)
            entity.definition_cid = definition_cid

    entity.name = form.name.data
    entity.definition = form.definition.data
    entity.updated_at = datetime.now(timezone.utc)

    enabled_field = getattr(form, 'enabled', None)
    if enabled_field is not None:
        entity.enabled = bool(enabled_field.data)

    template_field = getattr(form, 'template', None)
    if template_field is not None:
        entity.template = bool(template_field.data)

    save_entity(entity)

    if content_text is None:
        content_text = getattr(form, 'definition', None)
        if content_text is not None:
            content_text = content_text.data or ''
        else:
            content_text = ''

    record_entity_interaction(
        EntityInteractionRequest(
            user_id=entity.user_id,
            entity_type=entity_type,
            entity_name=entity.name,
            action='save',
            message=change_message or '',
            content=content_text,
        )
    )

    if type(entity).__name__ == 'Server':
        from .servers import update_server_definitions_cid

        update_server_definitions_cid(entity.user_id)
    elif type(entity).__name__ == 'Variable':
        from .variables import update_variable_definitions_cid

        update_variable_definitions_cid(entity.user_id)
    elif type(entity).__name__ == 'Secret':
        from .secrets import update_secret_definitions_cid

        update_secret_definitions_cid(entity.user_id)

    flash(f'{entity_type.title()} "{entity.name}" updated successfully!', 'success')
    return True


__all__ = ['check_name_exists', 'create_entity', 'update_entity']
