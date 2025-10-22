"""Helpers for provisioning the default AI stub server and alias."""

from __future__ import annotations

from typing import Optional

from flask import current_app

from alias_definition import (
    format_primary_alias_line,
    get_primary_alias_route,
    replace_primary_definition_line,
)
from db_access import (
    get_alias_by_name,
    get_server_by_name,
    save_entity,
)
from models import Alias, Server
from server_templates import iter_server_templates

AI_ALIAS_NAME = "ai"
AI_SERVER_NAME = "ai_stub"
AI_TEMPLATE_ID = "ai_stub"


def _get_ai_stub_definition() -> Optional[str]:
    """Load the ai_stub template definition from the bundled templates."""

    for template in iter_server_templates():
        if template.get("id") == AI_TEMPLATE_ID:
            definition = template.get("definition")
            if isinstance(definition, str):
                return definition
            break
    return None


def ensure_ai_stub_for_user(user_id: str) -> bool:
    """Ensure the default AI stub server and alias exist for the given user.

    Returns True when new resources were created, False otherwise.
    """

    if not user_id:
        return False

    # Respect any existing customisations.
    alias = get_alias_by_name(user_id, AI_ALIAS_NAME)
    if alias:
        primary_route = get_primary_alias_route(alias)
        if not primary_route:
            return False
        if primary_route.target_path not in {f"/{AI_SERVER_NAME}", f"{AI_SERVER_NAME}"}:
            return False

    if get_server_by_name(user_id, AI_ALIAS_NAME):
        return False

    definition = _get_ai_stub_definition()
    if definition is None:
        current_app.logger.warning("AI stub template definition is unavailable")
        return False

    created = False

    server = get_server_by_name(user_id, AI_SERVER_NAME)
    if server:
        if server.definition != definition:
            server.definition = definition
            save_entity(server)
            created = True
    else:
        server = Server(name=AI_SERVER_NAME, definition=definition, user_id=user_id)
        save_entity(server)
        created = True

    desired_target = f"/{AI_SERVER_NAME}"
    desired_pattern = f"/{AI_ALIAS_NAME}"
    if alias:
        primary_route = get_primary_alias_route(alias)
        needs_update = (
            not primary_route
            or primary_route.target_path != desired_target
            or primary_route.match_pattern != desired_pattern
            or primary_route.match_type != "literal"
            or primary_route.ignore_case
        )
        if needs_update:
            primary_line = format_primary_alias_line(
                "literal",
                desired_pattern,
                desired_target,
                ignore_case=False,
                alias_name=getattr(alias, "name", None),
            )
            alias.definition = replace_primary_definition_line(
                getattr(alias, "definition", None),
                primary_line,
            )
            save_entity(alias)
            created = True
    else:
        primary_line = format_primary_alias_line(
            "literal",
            desired_pattern,
            desired_target,
            ignore_case=False,
            alias_name=AI_ALIAS_NAME,
        )
        alias = Alias(
            name=AI_ALIAS_NAME,
            user_id=user_id,
            definition=primary_line,
        )
        save_entity(alias)
        created = True

    return created


def ensure_ai_stub_for_all_users() -> None:
    """Ensure the default user can use the AI stub without additional setup."""

    from identity import ensure_default_user

    user = ensure_default_user()
    ensure_ai_stub_for_user(user.id)


__all__ = [
    "ensure_ai_stub_for_all_users",
    "ensure_ai_stub_for_user",
]
