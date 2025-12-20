"""Generic CRUD route factory for entity management.

This module provides a factory for creating standard CRUD routes for entities
(servers, variables, secrets, aliases), eliminating ~200 lines of duplicate code.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from constants import ActionType
from db_access import delete_entity, save_entity
from interaction_log import load_interaction_history
from serialization import model_to_dict
from template_status import get_template_link_info

from .enabled import extract_enabled_value_from_request, request_prefers_json
from .entities import create_entity, update_entity
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
        get_by_name_func: Callable[[str], Any],
        *,
        get_entities_func: Callable[[], list],
        form_class: Type,
        # Optional customization
        param_name: Optional[
            str
        ] = None,  # URL parameter name (default: {entity_type}_name)
        update_cid_func: Optional[Callable[[str], Any]] = None,
        to_json_func: Optional[Callable[[Any], Dict[str, Any]]] = None,
        # Template names
        list_template: Optional[str] = None,
        view_template: Optional[str] = None,
        form_template: Optional[str] = None,
        # Extra context builders for views
        build_list_context: Optional[Callable[[list, str], Dict[str, Any]]] = None,
        build_view_context: Optional[Callable[[Any, str], Dict[str, Any]]] = None,
        # Form route customization
        get_templates_func: Optional[Callable[[], list]] = None,
        prepare_form_func: Optional[Callable[[Any], None]] = None,
        build_new_context: Optional[Callable[[Any], Dict[str, Any]]] = None,
        build_edit_context: Optional[Callable[[Any, Any], Dict[str, Any]]] = None,
        handle_save_as: bool = False,
    ):
        """Initialize entity route configuration.

        Args:
            entity_class: The model class (Server, Variable, Secret, Alias)
            entity_type: String identifier ('server', 'variable', 'secret', 'alias')
            plural_name: Plural form for URLs ('servers', 'variables', etc.)
            get_by_name_func: Function to get an entity by name.
            get_entities_func: Function to get the full collection of entities.
            form_class: WTForms form class for this entity
            param_name: URL parameter name for entity routes (default: {entity_type}_name)
            update_cid_func: Optional function to update CID after changes.
            to_json_func: Optional function to convert entity to JSON: (entity) -> dict
            list_template: Optional template name for list view (default: {plural_name}.html)
            view_template: Optional template name for view page (default: {entity_type}_view.html)
            form_template: Optional template name for create/edit forms.
            build_list_context: Optional function to build extra list context.
            build_view_context: Optional function to build extra view context.
            get_templates_func: Optional function to retrieve entity templates.
            prepare_form_func: Optional function to modify form after instantiation (e.g. set defaults).
            build_new_context: Optional function to build extra context for new route.
            build_edit_context: Optional function to build extra context for edit route.
            handle_save_as: Whether to support "Save As" functionality (default: False).
        """
        self.entity_class = entity_class
        self.entity_type = entity_type
        self.plural_name = plural_name
        self.param_name = param_name or f"{entity_type}_name"
        self.get_by_name = get_by_name_func
        self.get_entities = get_entities_func
        self.form_class = form_class
        self.update_cid = update_cid_func
        self.to_json = to_json_func or model_to_dict
        self.list_template = list_template or f"{plural_name}.html"
        self.view_template = view_template or f"{entity_type}_view.html"
        self.form_template = form_template
        self.build_list_context = build_list_context
        self.build_view_context = build_view_context
        self.get_templates = get_templates_func
        self.prepare_form = prepare_form_func
        self.build_new_context = build_new_context
        self.build_edit_context = build_edit_context
        self.handle_save_as = handle_save_as


def create_list_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[[], Any]:
    """Create the list route: GET /{entities}

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = config.plural_name

    @bp.route(f"/{config.plural_name}", endpoint=endpoint_name)
    def list_entities() -> Any:
        """List all entities."""
        entities_list = config.get_entities()

        if wants_structured_response():
            return jsonify([config.to_json(e) for e in entities_list])

        context = {config.plural_name: entities_list}

        # Add entity-specific list context
        if config.build_list_context:
            extra_context = config.build_list_context(entities_list)
            context.update(extra_context)

        # Add CID if available
        if config.update_cid and entities_list:
            cid = config.update_cid()
            context[f"{config.entity_type}_definitions_cid"] = cid

        return render_template(config.list_template, **context)

    list_entities.__name__ = endpoint_name
    return list_entities


def create_view_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the view route: GET /{entities}/<name>

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = f"view_{config.entity_type}"

    @bp.route(f"/{config.plural_name}/<{config.param_name}>", endpoint=endpoint_name)
    def view_entity(**kwargs: Any) -> Any:
        """View a specific entity."""
        entity_name = kwargs[config.param_name]
        entity = config.get_by_name(entity_name)
        if not entity:
            abort(404)

        if wants_structured_response():
            return jsonify(config.to_json(entity))

        context = {config.entity_type: entity}

        # Add entity-specific view context
        if config.build_view_context:
            extra_context = config.build_view_context(entity)
            context.update(extra_context)

        return render_template(config.view_template, **context)

    view_entity.__name__ = endpoint_name
    return view_entity


def create_enabled_toggle_route(
    bp: Blueprint, config: EntityRouteConfig
) -> Callable[..., Any]:
    """Create the enabled toggle route: POST /{entities}/<name>/enabled

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = f"update_{config.entity_type}_enabled"

    @bp.route(
        f"/{config.plural_name}/<{config.param_name}>/enabled",
        methods=["POST"],
        endpoint=endpoint_name,
    )
    def update_entity_enabled(**kwargs: Any) -> Any:
        """Toggle the enabled status for an entity."""
        entity_name = kwargs[config.param_name]
        entity = config.get_by_name(entity_name)
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
            config.update_cid()

        if request_prefers_json():
            return jsonify({config.entity_type: entity.name, "enabled": entity.enabled})

        return redirect(url_for(f"main.{config.plural_name}"))

    update_entity_enabled.__name__ = endpoint_name
    return update_entity_enabled


def create_delete_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the delete route: POST /{entities}/<name>/delete

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = f"delete_{config.entity_type}"

    @bp.route(
        f"/{config.plural_name}/<{config.param_name}>/delete",
        methods=["POST"],
        endpoint=endpoint_name,
    )
    def delete_entity_route(**kwargs: Any) -> Any:
        """Delete a specific entity."""
        entity_name = kwargs[config.param_name]
        entity = config.get_by_name(entity_name)
        if not entity:
            abort(404)

        delete_entity(entity)

        if config.update_cid:
            config.update_cid()

        flash(EntityMessages.deleted(config.entity_type, entity_name), "success")
        return redirect(url_for(f"main.{config.plural_name}"))

    delete_entity_route.__name__ = endpoint_name
    return delete_entity_route


def create_new_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the new entity route: GET/POST /{entities}/new

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = f"new_{config.entity_type}"

    @bp.route(
        f"/{config.plural_name}/new", methods=["GET", "POST"], endpoint=endpoint_name
    )
    def new_entity() -> Any:
        """Create a new entity."""
        form = config.form_class()

        if config.prepare_form:
            config.prepare_form(form)

        change_message = (request.form.get("change_message") or "").strip()
        definition_text = form.definition.data or ""

        entity_templates = []
        if config.get_templates:
            raw_templates = config.get_templates()
            entity_templates = [
                {
                    "id": getattr(t, "template_key", None)
                    or (f"user-{t.id}" if getattr(t, "id", None) else None),
                    "name": t.name,
                    "definition": t.definition or "",
                    "suggested_name": f"{t.name}-copy" if t.name else "",
                }
                for t in raw_templates
            ]

        if form.validate_on_submit():
            if create_entity(
                config.entity_class,
                form,
                config.entity_type,
                change_message=change_message,
                content_text=definition_text,
            ):
                return redirect(url_for(f"main.{config.plural_name}"))

        entity_name_hint = (form.name.data or "").strip()
        interaction_history = load_interaction_history(
            config.entity_type, entity_name_hint
        )

        template_link_info = get_template_link_info(config.plural_name)

        context = {
            "form": form,
            "title": f"Create New {config.entity_type.title()}",
            config.entity_type: None,
            "interaction_history": interaction_history,
            "ai_entity_name": entity_name_hint,
            "ai_entity_name_field": form.name.id,
            "template_link_info": template_link_info,
        }

        # Server templates use a specific key in the template
        if config.entity_type == "server":
            context["saved_server_templates"] = entity_templates
        else:
            context[f"{config.entity_type}_templates"] = entity_templates

        if config.build_new_context:
            context.update(config.build_new_context(form))

        return render_template(config.form_template, **context)

    new_entity.__name__ = endpoint_name
    return new_entity


def create_edit_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the edit entity route: GET/POST /{entities}/<name>/edit

    Args:
        bp: Flask blueprint to register route on
        config: Entity configuration

    Returns:
        The route function
    """
    endpoint_name = f"edit_{config.entity_type}"

    @bp.route(
        f"/{config.plural_name}/<{config.param_name}>/edit",
        methods=["GET", "POST"],
        endpoint=endpoint_name,
    )
    def edit_entity(**kwargs: Any) -> Any:
        """Edit a specific entity."""
        entity_name = kwargs[config.param_name]
        entity = config.get_by_name(entity_name)
        if not entity:
            abort(404)

        form = config.form_class(obj=entity)

        change_message = (request.form.get("change_message") or "").strip()
        # Use form definition if available (on error resubmit), otherwise entity definition
        definition_text = (
            form.definition.data
            if form.definition.data is not None
            else (entity.definition or "")
        )

        if form.validate_on_submit():
            save_action = (request.form.get("submit_action") or "").strip().lower()

            if config.handle_save_as and save_action == ActionType.SAVE_AS.value:
                # Treat 'Save As' as creating a new entity
                if create_entity(
                    config.entity_class,
                    form,
                    config.entity_type,
                    change_message=change_message,
                    content_text=definition_text,
                ):
                    return redirect(
                        url_for(
                            f"main.view_{config.entity_type}",
                            **{config.param_name: form.name.data},
                        )
                    )
            else:
                if update_entity(
                    entity,
                    form,
                    config.entity_type,
                    change_message=change_message,
                    content_text=definition_text,
                ):
                    return redirect(
                        url_for(
                            f"main.view_{config.entity_type}",
                            **{config.param_name: entity.name},
                        )
                    )

        interaction_history = load_interaction_history(config.entity_type, entity.name)

        context = {
            "form": form,
            "title": f'Edit {config.entity_type.title()} "{entity.name}"',
            config.entity_type: entity,
            "interaction_history": interaction_history,
            "ai_entity_name": entity.name,
            "ai_entity_name_field": form.name.id,
        }

        if config.build_edit_context:
            context.update(config.build_edit_context(form, entity))

        return render_template(config.form_template, **context)

    edit_entity.__name__ = endpoint_name
    return edit_entity


def register_standard_crud_routes(bp: Blueprint, config: EntityRouteConfig):
    """Register all standard CRUD routes for an entity type.

    This creates and registers the following routes:
    - GET /{entities} - List all entities
    - GET /{entities}/<name> - View specific entity
    - POST /{entities}/<name>/enabled - Toggle enabled status
    - POST /{entities}/<name>/delete - Delete entity

    If `form_template` is provided in the configuration, the following routes
    are also registered:
    - GET/POST /{entities}/new - Create new entity
    - GET/POST /{entities}/<name>/edit - Edit entity

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
        ...     get_entities_func=get_variables,
        ...     form_class=VariableForm,
        ...     update_cid_func=update_variable_definitions_cid,
        ... )
        >>> register_standard_crud_routes(main_bp, config)
    """
    create_list_route(bp, config)
    create_view_route(bp, config)
    create_enabled_toggle_route(bp, config)
    create_delete_route(bp, config)

    if config.form_template:
        create_new_route(bp, config)
        create_edit_route(bp, config)


__all__ = [
    "EntityRouteConfig",
    "register_standard_crud_routes",
    "create_list_route",
    "create_view_route",
    "create_enabled_toggle_route",
    "create_delete_route",
    "create_new_route",
    "create_edit_route",
]
