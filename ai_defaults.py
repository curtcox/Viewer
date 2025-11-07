"""Helpers for provisioning the default AI stub server and alias."""

from __future__ import annotations

from typing import Optional

from flask import current_app

from alias_definition import format_primary_alias_line
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

    alias = get_alias_by_name(user_id, AI_ALIAS_NAME)

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
    primary_line = format_primary_alias_line(
        "literal",
        desired_pattern,
        desired_target,
        ignore_case=False,
        alias_name=AI_ALIAS_NAME,
    )

    if alias:
        if alias.definition and alias.definition.strip():
            return created
        alias.definition = primary_line
        save_entity(alias)
        return True

    alias = Alias(
        name=AI_ALIAS_NAME,
        user_id=user_id,
        definition=primary_line,
    )
    save_entity(alias)
    return True


__all__ = [
    "ensure_ai_stub_for_user",
]
