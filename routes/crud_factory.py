"""Generic CRUD route factory for entity management.

This module provides a factory for creating standard CRUD routes for entities
(servers, variables, secrets, aliases), eliminating ~200 lines of duplicate code.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, url_for

from db_access import delete_entity, save_entity
from identity import current_user
from serialization import model_to_dict

from .enabled import extract_enabled_value_from_request, request_prefers_json
from .messages import EntityMessages
from .response_utils import wants_structured_response


class EntityRouteConfig:
    """Configuration for entity-specific CRUD routes.

    This class encapsulates all entity-specific behavior that differs between
    servers, variables, secrets, and aliases.
    """

    def __init__(
        self,
        entity_class: Type,
        entity_type: str,  # 'server', 'variable', 'secret', 'alias'
        plural_name: str,  # 'servers', 'variables', etc.
        get_by_name_func: Callable[[str, str], Any],
        get_user_entities_func: Callable[[str], list],
        form_class: Type,
        # Optional customization
        update_cid_func: Optional[Callable[[str], Any]] = None,
        to_json_func: Optional[Callable[[Any], Dict[str, Any]]] = None,
        # Template names
        list_template: Optional[str] = None,
        view_template: Optional[str] = None,
        # Extra context builders for views
        build_list_context: Optional[Callable[[list, str], Dict[str, Any]]] = None,
        build_view_context: Optional[Callable[[Any, str], Dict[str, Any]]] = None,
    ):
        """Initialize entity route configuration.

        Args:
            entity_class: The model class (Server, Variable, Secret, Alias)
            entity_type: String identifier ('server', 'variable', 'secret', 'alias')
            plural_name: Plural form for URLs ('servers', 'variables', etc.)
            get_by_name_func: Function to get entity by name: (user_id, name) -> entity
            get_user_entities_func: Function to get all user entities: (user_id) -> list
            form_class: WTForms form class for this entity
            update_cid_func: Optional function to update CID after changes: (user_id) -> cid
            to_json_func: Optional function to convert entity to JSON: (entity) -> dict
            list_template: Optional template name for list view (default: {plural_name}.html)
            view_template: Optional template name for view page (default: {entity_type}_view.html)
            build_list_context: Optional function to build extra list context: (entities, user_id) -> dict
            build_view_context: Optional function to build extra view context: (entity, user_id) -> dict
        """
        self.entity_class = entity_class
        self.entity_type = entity_type
        self.plural_name = plural_name
        self.get_by_name = get_by_name_func
        self.get_user_entities = get_user_entities_func
        self.form_class = form_class
        self.update_cid = update_cid_func
        self.to_json = to_json_func or model_to_dict
        self.list_template = list_template or f'{plural_name}.html'
        self.view_template = view_template or f'{entity_type}_view.html'
        self.build_list_context = build_list_context
        self.build_view_context = build_view_context


def create_list_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the list route: GET /{entities}

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    @bp.route(f'/{config.plural_name}')
    def list_entities():
        """List all entities for the current user."""
        entities_list = config.get_user_entities(current_user.id)

        if wants_structured_response():
            return jsonify([config.to_json(e) for e in entities_list])

        context = {config.plural_name: entities_list}

        # Add entity-specific list context
        if config.build_list_context:
            extra_context = config.build_list_context(entities_list, current_user.id)
            context.update(extra_context)

        # Add CID if available
        if config.update_cid and entities_list:
            cid = config.update_cid(current_user.id)
            context[f'{config.entity_type}_definitions_cid'] = cid

        return render_template(config.list_template, **context)

    list_entities.__name__ = config.plural_name
    return list_entities


def create_view_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the view route: GET /{entities}/<name>

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    @bp.route(f'/{config.plural_name}/<entity_name>')
    def view_entity(entity_name: str):
        """View a specific entity."""
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        if wants_structured_response():
            return jsonify(config.to_json(entity))

        context = {config.entity_type: entity}

        # Add entity-specific view context
        if config.build_view_context:
            extra_context = config.build_view_context(entity, current_user.id)
            context.update(extra_context)

        return render_template(config.view_template, **context)

    view_entity.__name__ = f'view_{config.entity_type}'
    return view_entity


def create_enabled_toggle_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the enabled toggle route: POST /{entities}/<name>/enabled

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    @bp.route(f'/{config.plural_name}/<entity_name>/enabled', methods=['POST'])
    def update_entity_enabled(entity_name: str):
        """Toggle the enabled status for an entity."""
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        try:
            enabled_value = extract_enabled_value_from_request()
        except ValueError:
            abort(400)

        entity.enabled = enabled_value
        entity.updated_at = datetime.now(timezone.utc)
        save_entity(entity)

        if config.update_cid:
            config.update_cid(current_user.id)

        if request_prefers_json():
            return jsonify({config.entity_type: entity.name, 'enabled': entity.enabled})

        return redirect(url_for(f'main.{config.plural_name}'))

    update_entity_enabled.__name__ = f'update_{config.entity_type}_enabled'
    return update_entity_enabled


def create_delete_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the delete route: POST /{entities}/<name>/delete

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    @bp.route(f'/{config.plural_name}/<entity_name>/delete', methods=['POST'])
    def delete_entity_route(entity_name: str):
        """Delete a specific entity."""
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        delete_entity(entity)

        if config.update_cid:
            config.update_cid(current_user.id)

        flash(EntityMessages.deleted(config.entity_type, entity_name), 'success')
        return redirect(url_for(f'main.{config.plural_name}'))

    delete_entity_route.__name__ = f'delete_{config.entity_type}'
    return delete_entity_route


def register_standard_crud_routes(bp: Blueprint, config: EntityRouteConfig):
    """Register all standard CRUD routes for an entity type.

    This creates and registers the following routes:
    - GET /{entities} - List all entities
    - GET /{entities}/<name> - View specific entity
    - POST /{entities}/<name>/enabled - Toggle enabled status
    - POST /{entities}/<name>/delete - Delete entity

    Note: New and Edit routes are not included as they have more complex
    entity-specific logic that varies significantly.

    Args:
        bp: Flask blueprint to register routes on
        config: Entity configuration

    Example:
        >>> from routes.crud_factory import EntityRouteConfig, register_standard_crud_routes
        >>> from models import Variable
        >>> from forms import VariableForm
        >>> config = EntityRouteConfig(
        ...     entity_class=Variable,
        ...     entity_type='variable',
        ...     plural_name='variables',
        ...     get_by_name_func=get_variable_by_name,
        ...     get_user_entities_func=get_user_variables,
        ...     form_class=VariableForm,
        ...     update_cid_func=update_variable_definitions_cid,
        ... )
        >>> register_standard_crud_routes(main_bp, config)
    """
    create_list_route(bp, config)
    create_view_route(bp, config)
    create_enabled_toggle_route(bp, config)
    create_delete_route(bp, config)


__all__ = [
    'EntityRouteConfig',
    'register_standard_crud_routes',
    'create_list_route',
    'create_view_route',
    'create_enabled_toggle_route',
    'create_delete_route',
]
